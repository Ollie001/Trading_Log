# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Ongoing improvements and feature experiments.

# Changelog

## [v1.1.0] - 2025-07-15

### Added
- Slider to filter by **minimum number of trades** in both:
  - **Win Rate by Confluence** tab
  - **Confluence Pair Stats** tab

### Changed
- Made the **plot themes dynamic** with a dropdown selector in the menu:
  - Default **Dark Theme**
  - Optional **Blue & White Theme**

### Fixed
- Ensured trade count filters properly re-render plots and stats when adjusted.
- Improved consistency of figure updates when switching datasets or themes.

---

## [v1.0.0] - 2025-07-14

### Added
- GUI-based app using Tkinter with notebook tabs:
  - **Equity Curve**
  - **Win Rate by Confluence**
  - **Confluence Pair Stats**
- CSV import functionality
- "Save to CSV" button for exporting confluence pair stats

