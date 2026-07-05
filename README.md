# Neon Horizon ASCII

Render videos as pure ASCII animations in the terminal.

Python 외부 패키지는 필요 없고, `ffmpeg`만 있으면 됩니다.

## Windows PowerShell

```powershell
git clone https://github.com/deploy103/neon-horizon-ascii.git
cd neon-horizon-ascii
python .\ascii_cat.py .\path\to\video.mp4
```

Python/FFmpeg 설치까지 확인하면서 실행하려면:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run_windows.ps1 .\path\to\video.mp4
```

## VSCode

`Run and Debug` 패널에서 `Run ASCII Video`를 선택하면 입력 영상 경로를 물어봅니다.

`Missing required command: ffmpeg`가 나오면 PowerShell에서 먼저 설치하세요.

```powershell
winget install --id Gyan.FFmpeg -e --source winget
```

설치 후 VSCode 터미널을 닫고 새로 연 다음 확인합니다.

```powershell
ffmpeg -version
python .\ascii_cat.py .\path\to\video.mp4
```

## Usage

```powershell
python .\ascii_cat.py .\path\to\video.mp4
```

기본값은 순수 ASCII 문자만 사용합니다. 흰 배경을 비우고 명암과 윤곽선을 강화해서 알아보기 쉽게 렌더링합니다.

품질과 속도는 주로 `--cols`, `--fps`, `--zoom`으로 조절합니다. 피사체가 잘리면 `--zoom`을 낮추거나 `--y-shift`를 조절하세요.

- 추천값: `python .\ascii_cat.py .\path\to\video.mp4 --cols 120 --zoom 1.25 --fps 24`
- 더 디테일하게: `python .\ascii_cat.py .\path\to\video.mp4 --cols 150 --zoom 1.25 --fps 24`
- 더 가볍게: `python .\ascii_cat.py .\path\to\video.mp4 --cols 90 --fps 12`
- 피사체를 조금 더 크게: `python .\ascii_cat.py .\path\to\video.mp4 --zoom 1.35 --cols 120 --fps 24`
- 위쪽 여백 더 확보: `python .\ascii_cat.py .\path\to\video.mp4 --cols 120 --zoom 1.35 --y-shift -0.28 --fps 24`
- 윤곽을 더 강하게: `python .\ascii_cat.py .\path\to\video.mp4 --edge-weight 1.6 --contrast 2.9`
- 계속 반복: `python .\ascii_cat.py .\path\to\video.mp4 --loop`
