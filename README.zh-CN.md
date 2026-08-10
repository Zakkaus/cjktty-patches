[English](README.md) | [正體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

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

然后启用 `CONFIG_FONT_CJK_32x32=y`。如未应用数据补丁，此选项会编译 8 MiB 的全零数据，因此现在默认关闭。

必须使用 framebuffer console。`vgacon` 的字体只能容纳 256 个字形，因此无法显示 CJK。

## 历史

| 年份 | 位置 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)，由 microcai 维护，每个内核版本各有一个分支 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)，抽取为补丁集合 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)，仍在维护；本仓库由此派生 |

## 变更记录

变更记录未翻译，请参阅[英文 README 的 Changes 章节](README.md#changes)。

## 许可证

补丁采用 [GPL-2.0-only](LICENSE)，与补丁所新增文件中的许可证声明一致。

## 致谢

- [youbest](http://blog.chinaunix.net/uid/436750.html) 提供[原始 univt 补丁](https://github.com/zhmars/univt-patches/tree/master/v2.6)
- [microcai](https://github.com/microcai) 和 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) 提供原始 cjktty 补丁
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) 提供部分 univt 修改
- [Unifont](https://savannah.gnu.org/projects/unifont) 提供字体数据
- [Terminus Font](http://terminus-font.sourceforge.net) 提供字体数据
