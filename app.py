from flask import Flask, jsonify, request
import asyncio
import aiomysql
from dotenv import load_dotenv
import os

load_dotenv()  # Загружаем переменные из .env файла

local_mysql_host = os.getenv('MYSQL_HOST_LOCAL')
local_mysql_user = os.getenv('MYSQL_USER_LOCAL')
local_mysql_password = os.getenv('MYSQL_PASSWORD_LOCAL')
remote_mysql_host = os.getenv('MYSQL_HOST_REMOTE')
remote_mysql_user = os.getenv('MYSQL_USER_REMOTE')
remote_mysql_password = os.getenv('MYSQL_PASSWORD_REMOTE')



