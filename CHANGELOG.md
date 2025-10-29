# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Страница реализаций с автоматическим формированием начислений по спецификациям.
- Модальные формы редактирования и удаления для контрагентов, объектов, договоров и спецификаций.
### Changed
- Единый европейский формат дат (dd/mm/yyyy) во всех формах и списках.

## [0.1.0] - 2025-10-28
### Added
- Начальная настройка проекта: Flask, SQLAlchemy, структура папок.
- Модели базы данных для всех справочников (Контрагенты, Объекты, и т.д.).
- Модели для Договоров и Спецификаций.
- Базовый UI для управления Контрагентами, Объектами и Договорами.
- Возможность добавлять Спецификации на странице договора.
- Система ведения версий (`CHANGELOG.md`) и правила работы в Git.
