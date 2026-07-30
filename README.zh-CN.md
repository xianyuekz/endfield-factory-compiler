# Endfield Factory Compiler

[English](README.md)

[![CI](https://github.com/xianyuekz/endfield-factory-compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/xianyuekz/endfield-factory-compiler/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/xianyuekz/endfield-factory-compiler?style=flat)](https://github.com/xianyuekz/endfield-factory-compiler/stargazers)

> 一个实验性的离线工厂 EDA：配方综合、地区技术映射、设备放置、物流布线和
> DRC。

![自动生成的示例布局](docs/assets/demo/layout.svg)

这个仓库是一个小而完整的概念验证，不是对“做出完整游戏工具”的承诺。它尝试
把工厂规划问题建模为类似 FPGA 的物理设计流程：

```text
目标产物
  → 配方综合
  → 地区技术映射
  → 设备放置
  → 感知拥塞的 A* 物流布线
  → 设计规则检查
  → SVG + JSON + Markdown 报告
```

当前示例会把“每分钟 8 个控制核心”编译为 13 台设备、25 条物流路径，并通过
DRC。示例全部使用虚构数据，仓库不会分发游戏素材，也不会把未经核实的数据
描述成官方数值。

## 快速体验

需要 Python 3.11 或更高版本，没有第三方运行时依赖。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e .

efc validate-pack region-packs/demo-valley/region.json
efc validate-project examples/control-core.json
efc compile examples/control-core.json --out build/demo
```

用浏览器打开 `build/demo/layout.svg` 即可查看布局；机器可读的物理设计结果位于
`build/demo/plan.json`，可读的编译报告位于 `build/demo/report.md`。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 为什么使用地区包？

不同地区及游戏版本的设备、配方、占地和物流规则可能不同。因此编译器核心不
内置官方数据，而由带版本号的地区包提供“器件支持”，类似于在 Quartus 中按需
安装 FPGA 器件系列。

格式说明见[地区包规范](docs/REGION_PACKS.md)，示例见虚构的
[`demo-valley`](region-packs/demo-valley/region.json)。

工程还可以约束最大功耗、设备数量和物流格数量，详见
[工程文件规范](docs/PROJECTS.md)。

## 当前边界

已经实现：

- DAG 配方展开与设备数量计算
- 功耗预算计算
- 数据驱动的设备、配方、障碍物和物流能力
- 可避开障碍物的确定性分层放置
- 带交叉和转弯代价、感知拥塞的 A* 布线
- 物理设备之间感知产能的多对多流量分配
- 越界、重叠、功耗、单设备流量、物流容量及连通性 DRC
- 工程级功耗、设备数量和物流格约束
- 占地率、路线长度、转弯和交叉等物理设计指标
- 支持编辑器校验和自动补全的 JSON Schema
- 零依赖 JSON、SVG 和 Markdown 输出

暂不实现：

- 终末地官方蓝图代码导入或导出
- 解包或受版权保护的游戏素材
- 备选配方、副产物、流体及循环生产图
- 全局最优放置与协商拥塞布线
- GUI、账号和在线后端

这些边界是有意保留的，以便社区能够理解、复用和接手项目。

## 项目状态

本项目处于实验阶段，采用社区维护模式。欢迎贡献地区数据包、布局布线后端和
功能提案；不承诺响应时间，也明确欢迎新的维护者。

准备较大改动前，请阅读[架构说明](docs/ARCHITECTURE.md)和
[贡献指南](CONTRIBUTING.md)。
版本变化记录在[更新日志](CHANGELOG.md)中。
已知正确性问题按照优先级记录在[路线图](docs/ROADMAP.md)中。

## 免责声明

本项目是非官方的同人技术实验，与鹰角网络、Gryphline 以及《明日方舟：终末地》
的开发和发行方不存在从属或授权关系。相关商标归各自权利人所有。

项目采用 [MIT License](LICENSE)。
