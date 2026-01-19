@echo off
title Agent Amigos - ComfyUI Video Engine
echo Starting ComfyUI...
cd external\ComfyUI
call venv\Scripts\activate
python main.py --listen 127.0.0.1 --port 8188
pause
