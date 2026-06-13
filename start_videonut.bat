@echo off
set PYTHONIOENCODING=utf-8
REM Add local Python and FFmpeg to PATH for this session
set PATH=C:\Users\vamsh\Desktop\video_nut\_video_nut\python;C:\Users\vamsh\Desktop\video_nut\_video_nut\python\Scripts;C:\Users\vamsh\Desktop\video_nut\_video_nut\tools\bin;%PATH%

echo.
echo ====================================
echo   VideoNut Environment Ready!
echo   Python: C:\Users\vamsh\Desktop\video_nut\_video_nut\python
echo   FFmpeg: C:\Users\vamsh\Desktop\video_nut\_video_nut\tools\bin
echo ====================================
echo.
echo Starting gemini...
gemini
