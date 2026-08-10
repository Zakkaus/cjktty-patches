[English](README.md) | [正體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md)

# cjktty-patches

本倉庫維護 `gentoo-zh/overlay` 中 Gentoo 核心及部分 CachyOS、XanMod 核心所使用的 cjktty 補丁。

補丁源自 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，並有少量修改。

- 自 Linux 5.10 起，核心設定選項 `CONFIG_FONT_16x16_CJK` 已重新命名為 `CONFIG_FONT_CJK_16x16`。
- 若要在高解析度螢幕上使用較大的字型，建議套用 32x32 字型資料補丁。
- 補丁內建的字型預期搭配 8x16 或 16x32 字型使用。改用其他字型尺寸時，字元可能無法正確顯示。
- 目前的 CJK 點陣字型資料衍生自 [GNU Unifont](https://savannah.gnu.org/projects/unifont) 15.1.04。32x32 資料的半形字元範圍取自 [Terminus Font](http://terminus-font.sourceforge.net)，並經由主線核心的 `font_ter16x32.c` 引入。

## 使用

從 `v<major>.x/` 選擇 `major.minor` 與核心版本相符的補丁。假設本倉庫檢出於 `../cjktty-patches`，請在核心原始碼根目錄執行：

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/v6.x/cjktty-6.18.patch
```

啟用以下所有核心設定選項：

- `CONFIG_FONTS=y`
- `CONFIG_FONT_CJK_16x16=y`
- `CONFIG_FRAMEBUFFER_CONSOLE=y`

若要使用 32x32 字型，請另外套用其資料補丁：

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/cjktty-add-cjk32x32-font-data.patch
```

接著啟用 `CONFIG_FONT_CJK_32x32=y`。若未套用資料補丁，此選項會編譯 8 MiB 的全零資料，因此現在預設關閉。

必須使用 framebuffer console。`vgacon` 的字型只能容納 256 個字形，因此無法顯示 CJK。

## 歷史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 維護，每個核心版本各有一個分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取為補丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在維護；本倉庫由此分叉而來 |

## 變更記錄

變更記錄未翻譯，請參閱[英文 README 的 Changes 章節](README.md#changes)。

## 授權

補丁採用 [GPL-2.0](LICENSE)，與補丁檔案中的授權聲明一致。

## 致謝

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 補丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 與 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) 提供原始 cjktty 補丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字型資料
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字型資料
