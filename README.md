[简体中文](README.md) | [English](README.en.md) | [正體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# cjktty-patches

本仓库维护 `gentoo-zh/overlay` 中 Gentoo 内核及部分 CachyOS、XanMod 内核所使用的 cjktty 补丁。

补丁源自 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，并作了少量修改。

- 自 Linux 5.10 起，内核配置选项 `CONFIG_FONT_16x16_CJK` 已重命名为 `CONFIG_FONT_CJK_16x16`。
- 如需在高分辨率屏幕上使用较大的字体，建议应用 32x32 字体数据补丁。
- 补丁内置的字体预期与 8x16 或 16x32 字体配合使用。改用其他字体尺寸时，字符可能无法正确显示。
- 当前的 CJK 点阵字体数据衍生自 [GNU Unifont](https://savannah.gnu.org/projects/unifont) 15.1.04。32x32 数据的半角字符范围取自 [Terminus Font](http://terminus-font.sourceforge.net)，并通过主线内核的 `font_ter16x32.c` 引入。

## 使用

从 `v<major>.x/` 中选择 `major.minor` 与内核版本相符的补丁。假设本仓库检出于 `../cjktty-patches`，请在内核源码根目录执行：

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/v6.x/cjktty-6.18.patch
```

启用以下所有内核配置选项：

- `CONFIG_FONTS=y`
- `CONFIG_FONT_CJK_16x16=y`
- `CONFIG_FRAMEBUFFER_CONSOLE=y`

如需使用 32x32 字体，请另行应用其数据补丁：

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/cjktty-add-cjk32x32-font-data.patch
```

然后启用 `CONFIG_FONT_CJK_32x32=y`。该选项默认关闭。

必须使用 framebuffer console；`vgacon` 无法显示 CJK。

## 历史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 维护，每个内核版本各有一个分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取为补丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在维护；本仓库由此派生 |

## 变更记录

### 2026.8.11 / 5.10.264、5.15.215、6.1.182、6.6.151、6.12.103、6.18.44、7.1.8、7.2-rc7

- 为 kernel.org 当前列出的每个内核新增补丁。原有的长期支援补丁只能套用到各系列的 `.0` 版，而那些版本在 GCC 15.3 之下已经无法构建，因此对任何有人在用的内核都不适用。旧文件保持不动，下游 Manifest 钉着它们的哈希。
- 7.1.x 的旋转缓冲区改用 `kvmalloc_array` 预先分配。`font_data_rotate` 用 `kmalloc_array` 扩容，拿不到 32x32 字模所需的 8 MiB，失败时又保留原缓冲区且不报错，旋转因此只画出两个字形。
- 两个字体选项都关闭时不产生任何代码。此前只有字体注册被条件编译，补丁仍多出 4,246 字节 `.text` 并移动 88 个 fbcon 符号；现在 `vmlinux` 与未打补丁的构建完全相同。
- `CONFIG_FONT_CJK_32x32` 改为默认关闭。基础补丁中该字模为空，默认开启时把 8 MiB 全零编入内核且不报错，自 2021 年起如此。
- 在 `font_cjk_16x16.c` 与 `font_cjk_32x32.c` 中注明字模来源。
- 新增 `tools/gen-font.py`，从 GNU Unifont 的 `.hex` 与主线基础字体逐字节重建两份字模数据，并可输出可加载的 PSF2。变更记录原本记为 Unifont 13.0.06，实际是 15.1.04。
- 新增拆分形式：每个 Unifont 修订版一份字模补丁，每个内核一份约 800 行的代码补丁，移植从审阅 12 MB 文件变成审阅一份能读懂的差异。原有文件未改动。
- 新增 `tools/test-stress.sh`，在 KASAN、kmemleak 与 lockdep 之下反复执行 `setfont`、`chvt`、旋转与 fbcon 重新绑定。
- 两层测试新增 `--cjk32`，让 32x32 路径被测试而不是被关闭；控制台检查新增 `--cell`，采样格随基础字体变化。
- 新增 `tools/make-boot-testvm.sh` 与 `test-system.sh --bootloader`，经 GRUB 与 dracut initramfs 从磁盘启动，而不是用 QEMU 的 `-kernel`。
- 新增 `tools/test-loadable-font.sh`，并证明未编入任何 CJK 字模的内核可以通过 `KDFONTOP` 接收字模，设计记录在 `docs/loadable-font.md`。
- 新增持续集成、每日检查各系列是否仍能套用到当前版本、`LICENSE`、使用说明，以及日语、韩语、正体中文与简体中文的 README。

更早的记录未翻译，请参阅[英文 README 的 Changes 章节](README.en.md#changes)。

## 许可证

补丁采用 [GPL-2.0-only](LICENSE)，与补丁所新增文件中的许可证声明一致。

## 致谢

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 补丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 和 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) 提供原始 cjktty 补丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字体数据
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字体数据
