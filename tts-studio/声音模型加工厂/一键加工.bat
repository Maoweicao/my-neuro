@echo off
chcp 936
echo ���ڿ�ʼ...
cd /d %~dp0
call ..\..\my-neuro-env\Scripts\activate.bat
python ����.py
echo ִ�����
pause