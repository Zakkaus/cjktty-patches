[简体中文](README.md) | [English](README.en.md) | [正體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

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

接著啟用 `CONFIG_FONT_CJK_32x32=y`。該選項預設關閉。

必須使用 framebuffer console；`vgacon` 無法顯示 CJK。

## 歷史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 維護，每個核心版本各有一個分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取為補丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在維護；本倉庫由此分叉而來 |

## 變更記錄

### 2026.8.11 / 5.10.264、5.15.215、6.1.182、6.6.151、6.12.103、6.18.44、7.1.8、7.2-rc7

- 為 kernel.org 目前列出的每個核心新增補丁。原有的長期支援補丁只能套用到各系列的 `.0` 版，而那些版本在 GCC 15.3 之下已經無法建置，因此對任何有人在用的核心都不適用。舊檔案保持不動，下游 Manifest 釘著它們的雜湊。
- 7.1.x 的旋轉緩衝區改用 `kvmalloc_array` 預先配置。`font_data_rotate` 用 `kmalloc_array` 擴容，拿不到 32x32 字模所需的 8 MiB，失敗時又保留原緩衝區且不報錯，旋轉因此只畫出兩個字形。
- 兩個字型選項都關閉時不產生任何程式碼。此前只有字型註冊被條件編譯，補丁仍多出 4,246 位元組 `.text` 並移動 88 個 fbcon 符號；現在 `vmlinux` 與未打補丁的建置完全相同。
- `CONFIG_FONT_CJK_32x32` 改為預設關閉。基礎補丁中該字模為空，預設開啟時把 8 MiB 全零編入核心且不報錯，自 2021 年起如此。
- 在 `font_cjk_16x16.c` 與 `font_cjk_32x32.c` 中註明字模來源。
- 新增 `tools/gen-font.py`，從 GNU Unifont 的 `.hex` 與主線基礎字型逐位元組重建兩份字模資料，並可輸出可載入的 PSF2。變更記錄原本記為 Unifont 13.0.06，實際是 15.1.04。
- 新增拆分形式：每個 Unifont 修訂版一份字模補丁，每個核心一份約 800 行的程式碼補丁，移植從審閱 12 MB 檔案變成審閱一份讀得動的差異。原有檔案未改動。
- 新增 `tools/test-stress.sh`，在 KASAN、kmemleak 與 lockdep 之下反覆執行 `setfont`、`chvt`、旋轉與 fbcon 重新綁定。
- 兩層測試新增 `--cjk32`，讓 32x32 路徑被測試而不是被關閉；主控台檢查新增 `--cell`，取樣格隨基礎字型變化。
- 新增 `tools/make-boot-testvm.sh` 與 `test-system.sh --bootloader`，經 GRUB 與 dracut initramfs 從磁碟開機，而不是用 QEMU 的 `-kernel`。
- 新增 `tools/test-loadable-font.sh`，並證明未編入任何 CJK 字模的核心可以透過 `KDFONTOP` 接收字模，設計記錄在 `docs/loadable-font.md`。
- 新增持續整合、每日檢查各系列是否仍能套用到目前版本、`LICENSE`、使用說明，以及日語、韓語、正體中文與簡體中文的 README。

更早的記錄未翻譯，請參閱[英文 README 的 Changes 章節](README.en.md#changes)。

## 授權

補丁採用 [GPL-2.0-only](LICENSE)，與補丁所新增檔案中的授權聲明一致。

## 致謝

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 補丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 與 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) 提供原始 cjktty 補丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字型資料
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字型資料
