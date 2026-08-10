[简体中文](README.md) | [English](README.en.md) | [正體中文](README.zh-TW.md) | [日本語](README.ja.md) | [한국어](README.ko.md)

# cjktty-patches

이 저장소는 `gentoo-zh/overlay`에서 Gentoo 커널과 일부 CachyOS 및 XanMod 커널에 사용하는 cjktty 패치를 유지 관리합니다.

패치는 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)에서 가져왔으며 일부 수정이 적용되었습니다.

- Linux 5.10부터 커널 구성 옵션 `CONFIG_FONT_16x16_CJK`의 이름이 `CONFIG_FONT_CJK_16x16`으로 변경되었습니다.
- 고해상도 화면에서 더 큰 글꼴을 사용하려면 32x32 글꼴 데이터 패치를 적용하는 것이 좋습니다.
- 패치에 내장된 비트맵 글꼴은 8x16 또는 16x32 글꼴과 함께 사용할 것을 전제로 합니다. 다른 글꼴 크기로 변경하면 문자가 올바르게 표시되지 않을 수 있습니다.
- 현재 CJK 비트맵 데이터는 [GNU Unifont](https://savannah.gnu.org/projects/unifont) 15.1.04에서 파생되었습니다. 32x32 데이터의 반각 문자 범위는 메인라인 커널의 `font_ter16x32.c`를 통해 [Terminus Font](http://terminus-font.sourceforge.net)에서 가져왔습니다.

## 사용법

`v<major>.x/`에서 `major.minor`가 커널 버전과 일치하는 패치를 선택합니다. 이 저장소가 `../cjktty-patches`에 체크아웃되어 있다고 가정하고, 커널 소스 루트에서 다음 명령을 실행합니다.

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/v6.x/cjktty-6.18.patch
```

다음 커널 구성 옵션을 모두 활성화합니다.

- `CONFIG_FONTS=y`
- `CONFIG_FONT_CJK_16x16=y`
- `CONFIG_FRAMEBUFFER_CONSOLE=y`

32x32 글꼴을 사용하려면 해당 데이터 패치도 적용합니다.

```sh
patch -p1 --fuzz=0 < ../cjktty-patches/cjktty-add-cjk32x32-font-data.patch
```

그런 다음 `CONFIG_FONT_CJK_32x32=y` 를 활성화합니다. 이 옵션은 기본적으로 비활성화되어 있습니다.

프레임버퍼 콘솔이 필요합니다. `vgacon` 은 CJK 를 표시할 수 없습니다.

## 역사

| 연도 | 위치 |
|---|---|
| 2011–2020 | [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty). microcai가 유지 관리했으며 커널마다 브랜치 하나를 사용했습니다 |
| 2020–2024 | [zhmars/cjktty-patches](https://github.com/zhmars/cjktty-patches). 패치 모음으로 추출되었습니다 |
| 2022– | [bigshans/cjktty-patches](https://github.com/bigshans/cjktty-patches). 계속 유지 관리되고 있으며 이 저장소는 해당 저장소에서 포크되었습니다 |

## 변경 기록

번역되지 않은 변경 기록은 [영어 README의 Changes 절](README.en.md#changes)에 있습니다.

## 라이선스

패치는 패치가 추가하는 파일의 라이선스 선언과 동일한 [GPL-2.0-only](LICENSE) 라이선스로 배포됩니다.

## 감사의 말

- [youbest](http://blog.chinaunix.net/uid/436750.html)는 [원본 univt 패치](https://github.com/zhmars/univt-patches/tree/master/v2.6)를 제공했습니다.
- [microcai](https://github.com/microcai)와 [gentoo-zh/linux-cjktty](https://github.com/gentoo-zh/linux-cjktty)는 원본 cjktty 패치를 제공했습니다.
- [AOSC-Dev/aosc-os-abbs](https://github.com/AOSC-Dev/aosc-os-abbs)는 univt 수정 사항 일부를 제공했습니다.
- [Unifont](https://savannah.gnu.org/projects/unifont)는 글꼴 데이터를 제공했습니다.
- [Terminus Font](http://terminus-font.sourceforge.net)는 글꼴 데이터를 제공했습니다.
