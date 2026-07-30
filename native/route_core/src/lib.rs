//! Native routing kernels for Endfield Factory Compiler.
//!
//! The crate is intentionally separate from the Python package while the native
//! API is still settling. Its first job is to make the route-search hot loop
//! explicit, testable and ready for Python bindings.

#![forbid(unsafe_code)]

use std::cmp::Ordering;
use std::collections::BinaryHeap;

const DIRECTIONS: [(isize, isize); 4] = [(1, 0), (0, 1), (-1, 0), (0, -1)];
const STATE_DIRECTIONS: usize = 5;
const NO_DIRECTION: usize = 4;
const NO_PARENT: usize = usize::MAX;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SearchStatus {
    Found,
    BlockedEndpoint,
    Exhausted,
    InvalidInput,
}

#[derive(Clone, Copy, Debug, Default, Eq, PartialEq)]
pub struct SearchStats {
    pub expanded_states: u64,
    pub generated_states: u64,
    pub heap_pushes: u64,
    pub peak_frontier: usize,
}

#[derive(Clone, Debug, PartialEq)]
pub struct SearchResult {
    pub status: SearchStatus,
    pub path: Vec<usize>,
    pub stats: SearchStats,
}

impl SearchResult {
    fn empty(status: SearchStatus) -> Self {
        Self {
            status,
            path: Vec::new(),
            stats: SearchStats::default(),
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct SearchConfig {
    pub allow_crossings: bool,
    pub base_cost: f32,
    pub same_item_cost: f32,
    pub crossing_penalty: f32,
    pub bend_penalty: f32,
}

impl Default for SearchConfig {
    fn default() -> Self {
        Self {
            allow_crossings: true,
            base_cost: 1.0,
            same_item_cost: 0.65,
            crossing_penalty: 8.0,
            bend_penalty: 0.4,
        }
    }
}

impl SearchConfig {
    fn is_valid(self) -> bool {
        self.base_cost.is_finite()
            && self.same_item_cost.is_finite()
            && self.crossing_penalty.is_finite()
            && self.bend_penalty.is_finite()
            && self.base_cost > 0.0
            && self.same_item_cost > 0.0
            && self.crossing_penalty >= 0.0
            && self.bend_penalty >= 0.0
    }
}

#[derive(Clone, Copy, Debug)]
pub struct RouteGrid<'a> {
    pub width: usize,
    pub height: usize,
    pub blocked: &'a [bool],
    /// Occupying item bitset for each cell. Zero means empty.
    pub occupancy: &'a [u64],
}

impl RouteGrid<'_> {
    fn cell_count(self) -> Option<usize> {
        self.width.checked_mul(self.height)
    }

    fn state_count(self) -> Option<usize> {
        self.cell_count()?.checked_mul(STATE_DIRECTIONS)
    }

    fn is_valid(self) -> bool {
        let Some(cell_count) = self.cell_count() else {
            return false;
        };
        self.width > 0
            && self.height > 0
            && self.blocked.len() == cell_count
            && self.occupancy.len() == cell_count
    }

    fn point(self, cell: usize) -> (usize, usize) {
        (cell % self.width, cell / self.width)
    }
}

#[derive(Debug, Default)]
pub struct AStarWorkspace {
    came_from: Vec<usize>,
    cost: Vec<f32>,
    seen_epoch: Vec<u32>,
    closed_epoch: Vec<u32>,
    heap: BinaryHeap<QueueNode>,
    epoch: u32,
}

impl AStarWorkspace {
    pub fn new() -> Self {
        Self::default()
    }

    fn begin(&mut self, state_count: usize) -> u32 {
        if self.came_from.len() != state_count {
            self.came_from = vec![NO_PARENT; state_count];
            self.cost = vec![0.0; state_count];
            self.seen_epoch = vec![0; state_count];
            self.closed_epoch = vec![0; state_count];
            self.epoch = 0;
        }
        if self.epoch == u32::MAX {
            self.seen_epoch.fill(0);
            self.closed_epoch.fill(0);
            self.epoch = 0;
        }
        self.epoch += 1;
        self.heap.clear();
        self.epoch
    }
}

#[derive(Clone, Copy, Debug)]
struct QueueNode {
    priority: f32,
    serial: u64,
    state: usize,
}

impl Eq for QueueNode {}

impl PartialEq for QueueNode {
    fn eq(&self, other: &Self) -> bool {
        self.priority.to_bits() == other.priority.to_bits()
            && self.serial == other.serial
            && self.state == other.state
    }
}

impl Ord for QueueNode {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .priority
            .total_cmp(&self.priority)
            .then_with(|| other.serial.cmp(&self.serial))
            .then_with(|| other.state.cmp(&self.state))
    }
}

impl PartialOrd for QueueNode {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

pub fn route_astar(
    grid: RouteGrid<'_>,
    start: usize,
    goal: usize,
    item_bit: u64,
    config: SearchConfig,
    workspace: &mut AStarWorkspace,
) -> SearchResult {
    if !grid.is_valid() || !config.is_valid() || item_bit == 0 {
        return SearchResult::empty(SearchStatus::InvalidInput);
    }
    let cell_count = grid.cell_count().expect("validated grid cell count");
    let state_count = grid.state_count().expect("validated grid state count");
    if start >= cell_count || goal >= cell_count {
        return SearchResult::empty(SearchStatus::InvalidInput);
    }
    if grid.blocked[start] || grid.blocked[goal] {
        return SearchResult::empty(SearchStatus::BlockedEndpoint);
    }

    let epoch = workspace.begin(state_count);
    let start_state = start * STATE_DIRECTIONS + NO_DIRECTION;
    let (goal_x, goal_y) = grid.point(goal);
    let mut serial = 1_u64;
    let mut stats = SearchStats {
        generated_states: 1,
        heap_pushes: 1,
        peak_frontier: 1,
        ..SearchStats::default()
    };

    workspace.came_from[start_state] = NO_PARENT;
    workspace.cost[start_state] = 0.0;
    workspace.seen_epoch[start_state] = epoch;
    workspace.heap.push(QueueNode {
        priority: 0.0,
        serial: 0,
        state: start_state,
    });

    while let Some(node) = workspace.heap.pop() {
        if workspace.closed_epoch[node.state] == epoch {
            continue;
        }
        workspace.closed_epoch[node.state] = epoch;
        stats.expanded_states += 1;

        let current = node.state / STATE_DIRECTIONS;
        let previous_direction = node.state % STATE_DIRECTIONS;
        if current == goal {
            return SearchResult {
                status: SearchStatus::Found,
                path: reconstruct_path(&workspace.came_from, node.state),
                stats,
            };
        }

        let (x, y) = grid.point(current);
        for (direction, (dx, dy)) in DIRECTIONS.iter().enumerate() {
            let Some(nx) = x.checked_add_signed(*dx) else {
                continue;
            };
            let Some(ny) = y.checked_add_signed(*dy) else {
                continue;
            };
            if nx >= grid.width || ny >= grid.height {
                continue;
            }

            let neighbor = ny * grid.width + nx;
            if grid.blocked[neighbor] {
                continue;
            }

            let occupied_mask = grid.occupancy[neighbor];
            let has_same_item = occupied_mask & item_bit != 0;
            let has_different_item = occupied_mask & !item_bit != 0;
            if has_different_item && !config.allow_crossings {
                continue;
            }

            let mut step_cost = if has_same_item {
                config.same_item_cost
            } else {
                config.base_cost
            };
            if has_different_item {
                step_cost += config.crossing_penalty;
            }
            if previous_direction != NO_DIRECTION && direction != previous_direction {
                step_cost += config.bend_penalty;
            }

            let neighbor_state = neighbor * STATE_DIRECTIONS + direction;
            let new_cost = workspace.cost[node.state] + step_cost;
            if workspace.seen_epoch[neighbor_state] != epoch
                || new_cost < workspace.cost[neighbor_state]
            {
                workspace.seen_epoch[neighbor_state] = epoch;
                workspace.cost[neighbor_state] = new_cost;
                workspace.came_from[neighbor_state] = node.state;
                let dx = goal_x.abs_diff(nx) as f32;
                let dy = goal_y.abs_diff(ny) as f32;
                let heuristic = config.same_item_cost * (dx + dy);
                workspace.heap.push(QueueNode {
                    priority: new_cost + heuristic,
                    serial,
                    state: neighbor_state,
                });
                serial += 1;
                stats.generated_states += 1;
                stats.heap_pushes += 1;
                stats.peak_frontier = stats.peak_frontier.max(workspace.heap.len());
            }
        }
    }

    SearchResult {
        status: SearchStatus::Exhausted,
        path: Vec::new(),
        stats,
    }
}

fn reconstruct_path(came_from: &[usize], mut state: usize) -> Vec<usize> {
    let mut path = Vec::new();
    loop {
        path.push(state / STATE_DIRECTIONS);
        let parent = came_from[state];
        if parent == NO_PARENT {
            break;
        }
        state = parent;
    }
    path.reverse();
    path
}

#[cfg(test)]
mod tests {
    use super::*;

    fn empty_grid(width: usize, height: usize) -> (Vec<bool>, Vec<u64>) {
        let cells = width * height;
        (vec![false; cells], vec![0; cells])
    }

    #[test]
    fn routes_a_straight_line() {
        let (blocked, occupancy) = empty_grid(4, 1);
        let grid = RouteGrid {
            width: 4,
            height: 1,
            blocked: &blocked,
            occupancy: &occupancy,
        };
        let mut workspace = AStarWorkspace::new();

        let result = route_astar(grid, 0, 3, 1, SearchConfig::default(), &mut workspace);

        assert_eq!(result.status, SearchStatus::Found);
        assert_eq!(result.path, vec![0, 1, 2, 3]);
        assert!(result.stats.expanded_states > 0);
    }

    #[test]
    fn routes_around_blocked_cells() {
        let (mut blocked, occupancy) = empty_grid(3, 3);
        blocked[1] = true;
        let grid = RouteGrid {
            width: 3,
            height: 3,
            blocked: &blocked,
            occupancy: &occupancy,
        };
        let mut workspace = AStarWorkspace::new();

        let result = route_astar(grid, 0, 2, 1, SearchConfig::default(), &mut workspace);

        assert_eq!(result.status, SearchStatus::Found);
        assert_eq!(result.path.first(), Some(&0));
        assert_eq!(result.path.last(), Some(&2));
        assert!(!result.path.contains(&1));
    }

    #[test]
    fn respects_crossing_policy() {
        let (mut blocked, mut occupancy) = empty_grid(3, 2);
        blocked[3] = true;
        blocked[4] = true;
        blocked[5] = true;
        occupancy[1] = 2;
        let grid = RouteGrid {
            width: 3,
            height: 2,
            blocked: &blocked,
            occupancy: &occupancy,
        };
        let mut workspace = AStarWorkspace::new();
        let without_crossing = route_astar(
            grid,
            0,
            2,
            1,
            SearchConfig {
                allow_crossings: false,
                ..SearchConfig::default()
            },
            &mut workspace,
        );
        let with_crossing = route_astar(
            grid,
            0,
            2,
            1,
            SearchConfig {
                allow_crossings: true,
                ..SearchConfig::default()
            },
            &mut workspace,
        );

        assert_eq!(without_crossing.status, SearchStatus::Exhausted);
        assert_eq!(with_crossing.status, SearchStatus::Found);
        assert_eq!(with_crossing.path, vec![0, 1, 2]);
    }

    #[test]
    fn reuses_workspace_between_searches() {
        let (mut blocked, occupancy) = empty_grid(5, 2);
        blocked[1] = true;
        let grid = RouteGrid {
            width: 5,
            height: 2,
            blocked: &blocked,
            occupancy: &occupancy,
        };
        let mut workspace = AStarWorkspace::new();

        let first = route_astar(grid, 0, 4, 1, SearchConfig::default(), &mut workspace);
        let second = route_astar(grid, 5, 9, 1, SearchConfig::default(), &mut workspace);

        assert_eq!(first.status, SearchStatus::Found);
        assert_eq!(second.status, SearchStatus::Found);
        assert_eq!(second.path, vec![5, 6, 7, 8, 9]);
    }
}
