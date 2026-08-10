[English](README.md) | [正體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

# cjktty-patches

本倉庫為 `sys-kernel/gentoo-cjk-sources` 及以其建置的 Live 鏡像維護補丁。

補丁源自 [Gentoo-zh/linux-cjktty](https://github.com/Gentoo-zh/linux-cjktty)，並有少量修改。

- 自 Linux 5.10 起，核心設定選項 `CONFIG_FONT_16x16_CJK` 已重新命名為 `CONFIG_FONT_CJK_16x16`。
- 若要在高解析度螢幕上使用較大的字型，建議套用 32x32 字型資料補丁。
- 補丁內建的字型預期搭配 8x16 或 16x32 字型使用。改用其他字型尺寸時，字元可能無法正確顯示。

## 歷史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 維護，每個核心版本各有一個分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取為補丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在維護；本倉庫由此分叉而來 |

## 變更記錄

變更記錄未翻譯，請參閱[英文 README 的 Changes 章節](README.md#changes)。

## 致謝

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 補丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 與 [Gentoo-zh/linux-cjktty](https://github.com/Gentoo-zh/linux-cjktty) 提供原始 cjktty 補丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字型資料
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字型資料
