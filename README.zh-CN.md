[English](README.md) | [正體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

# cjktty-patches

本仓库为 `sys-kernel/gentoo-cjk-sources` 及基于该软件包构建的 Live 镜像维护补丁。

补丁源自 [Gentoo-zh/linux-cjktty](https://github.com/Gentoo-zh/linux-cjktty)，并作了少量修改。

- 自 Linux 5.10 起，内核配置选项 `CONFIG_FONT_16x16_CJK` 已重命名为 `CONFIG_FONT_CJK_16x16`。
- 如需在高分辨率屏幕上使用较大的字体，建议应用 32x32 字体数据补丁。
- 补丁内置的字体预期与 8x16 或 16x32 字体配合使用。改用其他字体尺寸时，字符可能无法正确显示。

## 历史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 维护，每个内核版本各有一个分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取为补丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在维护；本仓库由此派生 |

## 变更记录

变更记录未翻译，请参阅[英文 README 的 Changes 章节](README.md#changes)。

## 致谢

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 补丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 和 [Gentoo-zh/linux-cjktty](https://github.com/Gentoo-zh/linux-cjktty) 提供原始 cjktty 补丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字体数据
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字体数据
