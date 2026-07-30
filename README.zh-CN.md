# Endfield Factory Compiler

[English](README.md)

[![CI](https://github.com/xianyuekz/endfield-factory-compiler/actions/workflows/ci.yml/badge.svg)](https://github.com/xianyuekz/endfield-factory-compiler/actions/workflows/ci.yml)
[![GitHub stars](https://img.shields.io/github/stars/xianyuekz/endfield-factory-compiler?style=flat)](https://github.com/xianyuekz/endfield-factory-compiler/stargazers)

> 一个实验性的离线工厂 EDA：配方综合、地区技术映射、设备放置、物流布线和
> DRC。

![自动生成的示例布局](docs/assets/demo/layout.svg)
![自动生成的高容谷地电池布局](docs/assets/hc-valley-battery/layout.svg)

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

玩具示例会把“每分钟 8 个控制核心”编译为 13 台设备、25 条物流路径，并通过
DRC。仓库还包含第一个更接近真实终末地目标的研究示例：每分钟 6 个高容谷地
电池，并生成可审计的设备摆放与物流布线方案。

仓库不会分发官方游戏数据、素材或蓝图字符串。接近真实的示例会标记为社区资料
研究包，而不是官方权威导出。

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

efc validate-pack region-packs/valley-iv-research/region.json
efc validate-project examples/hc-valley-battery.json
efc compile examples/hc-valley-battery.json --out build/hc-valley-battery
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

第一个非玩具示例见[高容谷地电池](docs/HC_VALLEY_BATTERY.md)。它目前会输出
SVG、JSON 物理计划和 Markdown 报告；官方游戏蓝图代码导出会保留在适配器边界
之后，等格式足够明确并且允许支持后再做。

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
- 可替换的路由后端以及 CPU、搜索规模和超时遥测
- 社区资料高容谷地电池研究示例
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

## 性能契约

所有后端共用一份执行资源预算：

```bash
efc compile examples/control-core.json --out build/demo \
  --jobs 8 --seed 0 --time-limit 30
```

当前紧凑 A* 后端仍然是确定性的串行实现。请求多个作业时，它会明确报告
`1/N 实际/请求作业数`并产生 DRC 警告。Python 定位为 CLI 和数据编排层；
成熟后的性能热点应迁移到原生后端。详细设计见[性能与并行架构](docs/PERFORMANCE.md)，
可重复基准见[`compile_scaling.py`](benchmarks/compile_scaling.py)。

## 免责声明

本项目是非官方的同人技术实验，与鹰角网络、Gryphline 以及《明日方舟：终末地》
的开发和发行方不存在从属或授权关系。相关商标归各自权利人所有。

项目采用 [MIT License](LICENSE)。
