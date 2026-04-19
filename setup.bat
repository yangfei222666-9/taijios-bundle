@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
echo.
echo ================================
echo  TaijiOS 一键安装 (双击入口)
echo ================================
echo.
python setup.py
if errorlevel 1 goto error
echo.
echo ================================
echo  安装完成. 按任意键进入菜单.
echo ================================
pause >nul
python taijios.py
goto end

:error
echo.
echo 安装有问题. 看上面报错. 按键退出.
pause

:end
