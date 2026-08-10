[English](README.md) | [正體中文](README.zh-TW.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# cjktty-patches

このリポジトリでは、`gentoo-zh/overlay` が Gentoo カーネルと一部の CachyOS および XanMod カーネルで使用する cjktty パッチを保守しています。

パッチは [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) を基に、若干の変更を加えたものです。

- Linux 5.10 以降、カーネル設定オプション `CONFIG_FONT_16x16_CJK` は `CONFIG_FONT_CJK_16x16` に改名されました。
- 高解像度の画面でより大きなフォントを使用するには、32x32 フォントデータパッチを適用することが推奨されます。
- パッチに組み込まれたビットマップフォントは、8x16 または 16x32 のフォントとの併用を前提としています。他のフォントサイズに変更すると、文字が正しく表示されない可能性があります。
- 現在の CJK ビットマップデータは [GNU Unifont](https://savannah.gnu.org/projects/unifont) 15.1.04 から派生しています。32x32 データの半角文字範囲は、メインラインカーネルの `font_ter16x32.c` を介して [Terminus Font](http://terminus-font.sourceforge.net) から取得されています。

## 使用方法

`v<major>.x/` から、`major.minor` がカーネルバージョンと一致するパッチを選択します。このリポジトリが `../cjktty-patches` にチェックアウトされている場合、カーネルソースのルートディレクトリで次のコマンドを実行します。

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/v6.x/cjktty-6.18.patch
```

以下のカーネル設定オプションをすべて有効にします。

- `CONFIG_FONTS=y`
- `CONFIG_FONT_CJK_16x16=y`
- `CONFIG_FRAMEBUFFER_CONSOLE=y`

32x32 フォントを使用するには、そのデータパッチも適用します。

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/cjktty-add-cjk32x32-font-data.patch
```

続いて `CONFIG_FONT_CJK_32x32=y` を有効にします。データパッチを適用しない場合、このオプションは 8 MiB のゼロデータをコンパイルするため、現在はデフォルトで無効になっています。

フレームバッファコンソールが必要です。`vgacon` のフォントには 256 個のグリフしか格納できないため、CJK を表示できません。

## 履歴

| 年 | 所在 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)。microcai が保守し、カーネルごとに 1 つのブランチを使用していました |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches)。パッチ集として抽出されました |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches)。現在も保守されており、このリポジトリはここからフォークされました |

## 変更履歴

翻訳されていない変更履歴は、[英語版 README の Changes セクション](README.md#changes)にあります。

## ライセンス

パッチは [GPL-2.0-only](LICENSE) の下でライセンスされており、パッチによって追加されるファイル内のライセンス宣言と一致します。

## クレジット

- [youbest](http://blog.chinaunix.net/uid/436750.html) は[元の univt パッチ](https://github.com/zhmars/univt-patches/tree/master/v2.6)を提供しました。
- [microcai](https://github.com/microcai) と [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty) は元の cjktty パッチを提供しました。
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs) は univt の変更の一部を提供しました。
- [Unifont](https://savannah.gnu.org/projects/unifont) はフォントデータを提供しました。
- [Terminus Font](http://terminus-font.sourceforge.net) はフォントデータを提供しました。
