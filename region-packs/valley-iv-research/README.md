# Valley IV Research Pack

This pack is a community-data research fixture for generating a first HC Valley
Battery physical-design plan. It is not an official data export and does not
include game assets.

The recipe shape follows public community references:

- `HC Valley Battery` is packaged from `Steel Part x10` and
  `Dense Originium Powder x15`.
- Sandleaf is planted from Sandleaf Seed, then shredded into Sandleaf Powder.
- Dense Originium Powder is ground from Originium Powder and Sandleaf Powder.
- Steel Parts are produced through the Ferrium -> Ferrium Powder ->
  Dense Ferrium Powder -> Steel -> Steel Part chain.

The current schema cannot model by-products, selectable output filters, depot
bus ports, thermal banks or in-game blueprint strings. This pack deliberately
keeps the data narrow enough for the compiler's current synthesis, placement
and routing pipeline.

The logistics capacity is intentionally modeled as an abstract high-capacity
bus tile (`120/min`) because schema v1 does not yet describe individual belt
tiers, splitter/filter devices or multiple explicit ports per machine.

Useful public references:

- https://endfield.gg/recipes/tools_proc_battery_3_1/
- https://gist.github.com/for-the-zero/0fe692caaf41d9532fe3abdc306bd5f6
- https://gamewith.net/akendfield/72615
- https://www.gamersky.com/handbook/202601/2081317.shtml
