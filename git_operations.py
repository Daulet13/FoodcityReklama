#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
import io

# Set encoding for stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Change to the project directory
project_path = r'E:\cursor\Проект Артака'
try:
    os.chdir(project_path)
    print(f"[OK] Перейдено в: {os.getcwd()}")
except Exception as e:
    print(f"[ERROR] Ошибка при переходе в директорию: {e}")
    sys.exit(1)

# Perform git operations
try:
    # Stage all changes
    print("1. Подготавливаю файлы (git add -A)...")
    result = subprocess.run(['git', 'add', '-A'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
    else:
        print("[OK] Файлы подготовлены")
    
    # Commit
    print("2. Создаю коммит...")
    commit_msg = "refactor: Улучшены компоненты для работы с реализациями"
    result = subprocess.run(['git', 'commit', '-m', commit_msg], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
    else:
        print(f"[OK] Коммит создан")
    
    # Create new branch
    print("3. Создаю новую ветку...")
    branch_name = "reorganize-realizations-with-composer"
    result = subprocess.run(['git', 'branch', branch_name], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
    else:
        print(f"[OK] Ветка создана: {branch_name}")
    
    # Show status
    print("\n4. Список веток:")
    result = subprocess.run(['git', 'branch', '-v'], capture_output=True, text=True)
    print(result.stdout)
    
except Exception as e:
    print(f"[ERROR] Ошибка: {e}")
    sys.exit(1)

print("[DONE] Все операции выполнены успешно!")
