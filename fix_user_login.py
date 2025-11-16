#!/usr/bin/env python
"""
Скрипт для диагностики и исправления проблем с входом в систему.

Использование:
    python fix_user_login.py
"""

import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'financial_consolidator.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def list_users():
    """Показать всех пользователей в системе."""
    print("\n" + "="*60)
    print("СПИСОК ПОЛЬЗОВАТЕЛЕЙ В СИСТЕМЕ:")
    print("="*60)
    
    users = User.objects.all()
    if not users:
        print("❌ Пользователей не найдено!")
        return False
    
    for user in users:
        status = "✅ Активен" if user.is_active else "❌ Неактивен"
        staff = "👤 Staff" if user.is_staff else ""
        superuser = "🔑 Superuser" if user.is_superuser else ""
        print(f"\nUsername: {user.username}")
        print(f"  Email: {user.email or '(не указан)'}")
        print(f"  Статус: {status} {staff} {superuser}")
        print(f"  Последний вход: {user.last_login or 'никогда'}")
    
    return True

def create_superuser():
    """Создать нового суперпользователя."""
    print("\n" + "="*60)
    print("СОЗДАНИЕ НОВОГО СУПЕРПОЛЬЗОВАТЕЛЯ")
    print("="*60)
    
    username = input("\nВведите username: ").strip()
    if not username:
        print("❌ Username не может быть пустым!")
        return False
    
    if User.objects.filter(username=username).exists():
        print(f"❌ Пользователь '{username}' уже существует!")
        return False
    
    email = input("Введите email (опционально): ").strip()
    password = input("Введите пароль: ").strip()
    
    if not password:
        print("❌ Пароль не может быть пустым!")
        return False
    
    try:
        user = User.objects.create_superuser(
            username=username,
            email=email or '',
            password=password
        )
        print(f"\n✅ Суперпользователь '{username}' успешно создан!")
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании пользователя: {e}")
        return False

def reset_password():
    """Сбросить пароль существующего пользователя."""
    print("\n" + "="*60)
    print("СБРОС ПАРОЛЯ")
    print("="*60)
    
    username = input("\nВведите username пользователя: ").strip()
    if not username:
        print("❌ Username не может быть пустым!")
        return False
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ Пользователь '{username}' не найден!")
        return False
    
    new_password = input("Введите новый пароль: ").strip()
    if not new_password:
        print("❌ Пароль не может быть пустым!")
        return False
    
    user.set_password(new_password)
    user.save()
    print(f"\n✅ Пароль для пользователя '{username}' успешно изменен!")
    return True

def activate_user():
    """Активировать пользователя."""
    print("\n" + "="*60)
    print("АКТИВАЦИЯ ПОЛЬЗОВАТЕЛЯ")
    print("="*60)
    
    username = input("\nВведите username пользователя: ").strip()
    if not username:
        print("❌ Username не может быть пустым!")
        return False
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ Пользователь '{username}' не найден!")
        return False
    
    user.is_active = True
    user.save()
    print(f"\n✅ Пользователь '{username}' активирован!")
    return True

def test_login():
    """Протестировать вход с указанными credentials."""
    print("\n" + "="*60)
    print("ТЕСТ ВХОДА")
    print("="*60)
    
    username = input("\nВведите username: ").strip()
    password = input("Введите пароль: ").strip()
    
    user = authenticate(username=username, password=password)
    if user:
        if user.is_active:
            print(f"\n✅ Вход успешен! Пользователь '{username}' может войти в систему.")
            return True
        else:
            print(f"\n❌ Пользователь '{username}' найден, но НЕ АКТИВЕН!")
            print("   Используйте опцию 'Активировать пользователя' для исправления.")
            return False
    else:
        print(f"\n❌ Неверный username или пароль!")
        return False

def main():
    """Главное меню."""
    while True:
        print("\n" + "="*60)
        print("УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ И ВХОДОМ")
        print("="*60)
        print("\nВыберите действие:")
        print("1. Показать всех пользователей")
        print("2. Создать нового суперпользователя")
        print("3. Сбросить пароль пользователя")
        print("4. Активировать пользователя")
        print("5. Протестировать вход")
        print("0. Выход")
        
        choice = input("\nВаш выбор: ").strip()
        
        if choice == '0':
            print("\nДо свидания!")
            break
        elif choice == '1':
            list_users()
        elif choice == '2':
            create_superuser()
        elif choice == '3':
            reset_password()
        elif choice == '4':
            activate_user()
        elif choice == '5':
            test_login()
        else:
            print("\n❌ Неверный выбор! Попробуйте снова.")

if __name__ == '__main__':
    main()

