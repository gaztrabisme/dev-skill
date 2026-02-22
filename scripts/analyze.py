#!/usr/bin/env python3
"""
Codebase Analyzer

Combines file statistics and dependency analysis into a single tool.
Runs in three modes: stats (file metrics), deps (dependency graph), or full (both).

Usage:
    python analyze.py [directory]                  # default: full mode
    python analyze.py --mode stats [directory]
    python analyze.py --mode deps [directory]
    python analyze.py --mode full [directory]

Output is JSON to stdout, redirect to file:
    python analyze.py ./src > analysis.json

Note: Dependency analysis is STATIC only. It cannot detect:
    - Dynamic imports (importlib, __import__)
    - Plugin systems
    - External consumers of your code
    - Conditional imports that depend on runtime state

Use as a GUIDE, not ground truth.
"""

import argparse
import ast
import fnmatch
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# ──────────────────────────────────────────────
# Shared Utilities
# ──────────────────────────────────────────────

# Directories to always exclude
EXCLUDE_DIRS = {
    '__pycache__', '.git', '.venv', 'venv', 'env',
    'node_modules', '.tox', '.pytest_cache', '.mypy_cache',
    'dist', 'build', '.eggs', '.cache', 'coverage',
    '.next', '.nuxt', 'out', 'target'
}

# Files to exclude from stats
EXCLUDE_FILES = {
    'package-lock.json', 'yarn.lock', 'poetry.lock',
    'Pipfile.lock', 'composer.lock'
}

# File extensions to analyze (stats mode)
SOURCE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    '.ts': 'typescript', '.tsx': 'typescript',
    '.html': 'html', '.css': 'css', '.scss': 'scss', '.less': 'less',
    '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml', '.xml': 'xml',
    '.sh': 'shell', '.bash': 'shell', '.zsh': 'shell',
    '.go': 'go', '.rs': 'rust', '.java': 'java', '.kt': 'kotlin',
    '.c': 'c', '.cpp': 'cpp', '.h': 'c', '.hpp': 'cpp',
    '.rb': 'ruby', '.php': 'php', '.sql': 'sql',
    '.md': 'markdown', '.txt': 'text',
}


def parse_gitignore(root: Path) -> List[str]:
    """Parse .gitignore file and return list of patterns."""
    gitignore_path = root / ".gitignore"
    patterns = []

    if gitignore_path.exists():
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except Exception:
            pass

    return patterns


def matches_gitignore(path: Path, patterns: List[str], root: Path) -> bool:
    """Check if a path matches any gitignore pattern."""
    try:
        rel_path = path.relative_to(root)
    except ValueError:
        return False

    rel_str = str(rel_path)
    rel_parts = rel_path.parts

    for pattern in patterns:
        clean_pattern = pattern.rstrip("/")

        if "/" in clean_pattern:
            if rel_str.startswith(clean_pattern + "/") or rel_str == clean_pattern:
                return True
            if fnmatch.fnmatch(rel_str, clean_pattern) or fnmatch.fnmatch(rel_str, clean_pattern + "/*"):
                return True
        else:
            for part in rel_parts:
                if fnmatch.fnmatch(part, clean_pattern):
                    return True
            if fnmatch.fnmatch(rel_str, clean_pattern):
                return True

    return False


def should_skip_path(path: Path) -> bool:
    """Check if path should be skipped based on directory/file exclusions."""
    for part in path.parts:
        if part in EXCLUDE_DIRS:
            return True
        if part.endswith('.egg-info'):
            return True
    if path.name in EXCLUDE_FILES:
        return True
    return False


# ──────────────────────────────────────────────
# File Statistics Functions
# ──────────────────────────────────────────────

def find_source_files(directory: Path, gitignore_patterns: List[str]) -> List[Path]:
    """Find all source files in directory, respecting .gitignore."""
    source_files = []
    for ext in SOURCE_EXTENSIONS:
        for path in directory.rglob(f'*{ext}'):
            if should_skip_path(path):
                continue
            if matches_gitignore(path, gitignore_patterns, directory):
                continue
            source_files.append(path)
    return source_files


def count_lines(file_path: Path) -> Dict:
    """Count lines in a file (total, code, blank, comment)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        return {'error': str(e)}

    total = len(lines)
    blank = sum(1 for line in lines if line.strip() == '')
    comment = 0

    in_multiline = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            comment += 1
        elif stripped.startswith('//'):
            comment += 1
        elif '/*' in stripped and '*/' in stripped:
            comment += 1
        elif '/*' in stripped:
            in_multiline = True
            comment += 1
        elif '*/' in stripped:
            in_multiline = False
            comment += 1
        elif in_multiline:
            comment += 1
        elif stripped.startswith('"""') or stripped.startswith("'''"):
            comment += 1

    return {
        'total': total,
        'code': total - blank - comment,
        'blank': blank,
        'comment': comment
    }


def analyze_python_file(file_path: Path) -> Dict:
    """Detailed analysis for Python files (classes, functions)."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        return {'error': f'Syntax error: {e}'}
    except Exception as e:
        return {'error': str(e)}

    classes = []
    functions = []
    top_level_functions = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            methods = []
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({
                        'name': item.name,
                        'line': item.lineno,
                        'lines': (item.end_lineno or item.lineno) - item.lineno + 1,
                        'is_async': isinstance(item, ast.AsyncFunctionDef)
                    })
            classes.append({
                'name': node.name,
                'line': node.lineno,
                'lines': (node.end_lineno or node.lineno) - node.lineno + 1,
                'method_count': len(methods),
                'methods': methods
            })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                'name': node.name,
                'line': node.lineno,
                'lines': (node.end_lineno or node.lineno) - node.lineno + 1,
                'is_async': isinstance(node, ast.AsyncFunctionDef)
            }
            functions.append(func_info)
            top_level_functions.append(func_info)

    for cls in classes:
        functions.extend(cls['methods'])

    return {
        'class_count': len(classes),
        'function_count': len(functions),
        'top_level_function_count': len(top_level_functions),
        'classes': classes,
        'top_level_functions': top_level_functions
    }


def analyze_file(file_path: Path, project_root: Path) -> Dict:
    """Analyze a single file for stats."""
    rel_path = str(file_path.relative_to(project_root))
    ext = file_path.suffix.lower()
    language = SOURCE_EXTENSIONS.get(ext, 'unknown')

    line_info = count_lines(file_path)

    result = {
        'file': rel_path,
        'language': language,
        'extension': ext,
        'lines': line_info
    }

    if language == 'python' and 'error' not in line_info:
        python_info = analyze_python_file(file_path)
        if 'error' not in python_info:
            result['python'] = python_info

    if 'error' not in line_info:
        result['exceeds_500_lines'] = line_info['total'] > 500

    return result


def build_directory_tree(files: List[Dict], project_root: Path) -> Dict:
    """Build a directory tree structure with stats."""
    tree = {'name': project_root.name, 'type': 'directory', 'children': {}, 'stats': defaultdict(int)}

    for file_info in files:
        if 'error' in file_info.get('lines', {}):
            continue

        parts = Path(file_info['file']).parts
        current = tree

        for part in parts[:-1]:
            if part not in current['children']:
                current['children'][part] = {
                    'name': part,
                    'type': 'directory',
                    'children': {},
                    'stats': defaultdict(int)
                }
            current = current['children'][part]

        filename = parts[-1]
        current['children'][filename] = {
            'name': filename,
            'type': 'file',
            'lines': file_info['lines']['total'],
            'language': file_info['language']
        }

        lines = file_info['lines']['total']
        language = file_info['language']

        current_path = tree
        for part in parts[:-1]:
            current_path['stats']['files'] += 1
            current_path['stats']['lines'] += lines
            current_path['stats'][f'lines_{language}'] += lines
            current_path = current_path['children'][part]

        current_path['stats']['files'] += 1
        current_path['stats']['lines'] += lines
        current_path['stats'][f'lines_{language}'] += lines

    def convert_stats(node):
        if 'stats' in node:
            node['stats'] = dict(node['stats'])
        if 'children' in node:
            for child in node['children'].values():
                convert_stats(child)

    convert_stats(tree)
    return tree


def analyze_directory_stats(directory: str) -> Dict:
    """Analyze directory for file statistics."""
    project_root = Path(directory).resolve()

    if not project_root.exists():
        return {'error': f'Directory not found: {directory}'}

    gitignore_patterns = parse_gitignore(project_root)
    files = find_source_files(project_root, gitignore_patterns)

    if not files:
        return {'error': 'No source files found', 'directory': str(project_root)}

    file_stats = [analyze_file(f, project_root) for f in files]

    total_lines = 0
    total_code = 0
    total_blank = 0
    total_comment = 0
    files_over_500 = []
    by_language = defaultdict(lambda: {'files': 0, 'lines': 0})
    by_directory = defaultdict(lambda: {'files': 0, 'lines': 0})

    for stat in file_stats:
        if 'error' in stat.get('lines', {}):
            continue

        lines = stat['lines']
        total_lines += lines['total']
        total_code += lines['code']
        total_blank += lines['blank']
        total_comment += lines['comment']

        lang = stat['language']
        by_language[lang]['files'] += 1
        by_language[lang]['lines'] += lines['total']

        parts = Path(stat['file']).parts
        top_dir = parts[0] if len(parts) > 1 else '.'
        by_directory[top_dir]['files'] += 1
        by_directory[top_dir]['lines'] += lines['total']

        if stat.get('exceeds_500_lines'):
            files_over_500.append({
                'file': stat['file'],
                'lines': lines['total'],
                'language': lang
            })

    files_over_500.sort(key=lambda x: x['lines'], reverse=True)
    tree = build_directory_tree(file_stats, project_root)

    return {
        'directory': str(project_root),
        'summary': {
            'file_count': len(files),
            'total_lines': total_lines,
            'code_lines': total_code,
            'blank_lines': total_blank,
            'comment_lines': total_comment
        },
        'by_language': dict(by_language),
        'by_directory': dict(by_directory),
        'files_over_500_lines': files_over_500,
        'files_over_500_count': len(files_over_500),
        'all_files': file_stats,
        'directory_tree': tree
    }


# ──────────────────────────────────────────────
# Dependency Analysis Functions
# ──────────────────────────────────────────────

def find_python_files(directory: Path, gitignore_patterns: List[str]) -> List[Path]:
    """Find all Python files in directory, respecting .gitignore."""
    python_files = []
    for path in directory.rglob('*.py'):
        if should_skip_path(path):
            continue
        if matches_gitignore(path, gitignore_patterns, directory):
            continue
        python_files.append(path)
    return python_files


def extract_imports(file_path: Path, project_root: Path) -> Dict:
    """Extract import information from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        return {
            'file': str(file_path.relative_to(project_root)),
            'error': f'Syntax error: {e}',
            'imports': [],
            'from_imports': []
        }
    except Exception as e:
        return {
            'file': str(file_path.relative_to(project_root)),
            'error': str(e),
            'imports': [],
            'from_imports': []
        }

    imports = []
    from_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'module': alias.name,
                    'alias': alias.asname,
                    'line': node.lineno
                })
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            level = node.level

            for alias in node.names:
                from_imports.append({
                    'module': module,
                    'name': alias.name,
                    'alias': alias.asname,
                    'level': level,
                    'line': node.lineno
                })

    return {
        'file': str(file_path.relative_to(project_root)),
        'imports': imports,
        'from_imports': from_imports
    }


def resolve_relative_import(importing_file: Path, module: str, level: int, project_root: Path) -> Optional[str]:
    """Resolve a relative import to an absolute module path."""
    if level == 0:
        return module

    rel_path = importing_file.relative_to(project_root)
    parts = list(rel_path.parts[:-1])

    if level > len(parts):
        return None

    base_parts = parts[:len(parts) - level + 1]

    if module:
        return '.'.join(base_parts + module.split('.'))
    else:
        return '.'.join(base_parts)


def file_to_module(file_path: Path, project_root: Path) -> str:
    """Convert a file path to a module name."""
    rel_path = file_path.relative_to(project_root)
    parts = list(rel_path.parts)

    if parts[-1].endswith('.py'):
        parts[-1] = parts[-1][:-3]

    if parts[-1] == '__init__':
        parts = parts[:-1]

    return '.'.join(parts)


def build_dependency_graph(files: List[Path], project_root: Path) -> Dict:
    """Build a complete dependency graph."""

    module_to_file = {}
    file_to_module_map = {}

    for f in files:
        module = file_to_module(f, project_root)
        module_to_file[module] = str(f.relative_to(project_root))
        file_to_module_map[str(f.relative_to(project_root))] = module

    all_imports = [extract_imports(f, project_root) for f in files]

    imports_graph = defaultdict(set)
    imported_by = defaultdict(set)
    internal_modules = set(module_to_file.keys())
    external_deps = set()

    for file_data in all_imports:
        if 'error' in file_data and file_data.get('imports') == []:
            continue

        file_path = file_data['file']
        importing_module = file_to_module_map.get(file_path, file_path)

        for imp in file_data.get('imports', []):
            full_module = imp['module']
            top_level = full_module.split('.')[0]

            if any(full_module.startswith(internal) for internal in internal_modules):
                for internal in internal_modules:
                    if full_module.startswith(internal):
                        imports_graph[importing_module].add(internal)
                        imported_by[internal].add(importing_module)
                        break
            else:
                external_deps.add(top_level)

        for imp in file_data.get('from_imports', []):
            module = imp['module']
            level = imp['level']

            if level > 0:
                resolved = resolve_relative_import(
                    project_root / file_path, module, level, project_root
                )
                if resolved and resolved in internal_modules:
                    imports_graph[importing_module].add(resolved)
                    imported_by[resolved].add(importing_module)
            else:
                top_level = module.split('.')[0] if module else ''
                if any(module.startswith(internal) for internal in internal_modules):
                    for internal in internal_modules:
                        if module.startswith(internal):
                            imports_graph[importing_module].add(internal)
                            imported_by[internal].add(importing_module)
                            break
                elif top_level:
                    external_deps.add(top_level)

    imports_graph = {k: sorted(list(v)) for k, v in imports_graph.items()}
    imported_by = {k: sorted(list(v)) for k, v in imported_by.items()}

    return {
        'modules': module_to_file,
        'imports': imports_graph,
        'imported_by': imported_by,
        'external_dependencies': sorted(list(external_deps)),
        'file_imports': all_imports
    }


def find_circular_dependencies(imports_graph: Dict[str, List[str]]) -> List[List[str]]:
    """Find circular dependencies using DFS."""
    cycles = []
    visited = set()
    rec_stack = []
    rec_set = set()

    def dfs(node: str, path: List[str]):
        if node in rec_set:
            cycle_start = path.index(node)
            cycle = path[cycle_start:] + [node]
            min_idx = cycle.index(min(cycle[:-1]))
            normalized = cycle[min_idx:-1] + cycle[:min_idx] + [cycle[min_idx]]
            if normalized not in cycles:
                cycles.append(normalized)
            return

        if node in visited:
            return

        visited.add(node)
        rec_stack.append(node)
        rec_set.add(node)

        for neighbor in imports_graph.get(node, []):
            dfs(neighbor, path + [node])

        rec_set.remove(node)
        rec_stack.pop()

    for node in imports_graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def find_orphan_modules(modules: Dict[str, str], imported_by: Dict[str, List[str]], imports_graph: Dict[str, List[str]]) -> List[str]:
    """Find modules that are never imported by any other module."""
    orphans = []
    for module in modules:
        if module.endswith('__init__') or module.endswith('__main__'):
            continue
        if module not in imported_by or len(imported_by[module]) == 0:
            orphans.append(module)
    return orphans


def find_hotspots(imported_by: Dict[str, List[str]], threshold: int = 5) -> List[Dict]:
    """Find modules that are imported by many other modules."""
    hotspots = []
    for module, importers in imported_by.items():
        if len(importers) >= threshold:
            hotspots.append({
                'module': module,
                'imported_by_count': len(importers),
                'importers': importers
            })
    return sorted(hotspots, key=lambda x: x['imported_by_count'], reverse=True)


def analyze_directory_deps(directory: str) -> Dict:
    """Analyze directory for dependency information."""
    project_root = Path(directory).resolve()

    if not project_root.exists():
        return {'error': f'Directory not found: {directory}'}

    gitignore_patterns = parse_gitignore(project_root)
    files = find_python_files(project_root, gitignore_patterns)

    if not files:
        return {'error': 'No Python files found', 'directory': str(project_root)}

    graph = build_dependency_graph(files, project_root)

    circular = find_circular_dependencies(graph['imports'])
    orphans = find_orphan_modules(graph['modules'], graph['imported_by'], graph['imports'])
    hotspots = find_hotspots(graph['imported_by'])

    return {
        'directory': str(project_root),
        'file_count': len(files),
        'module_count': len(graph['modules']),
        'modules': graph['modules'],
        'imports': graph['imports'],
        'imported_by': graph['imported_by'],
        'external_dependencies': graph['external_dependencies'],
        'analysis': {
            'circular_dependencies': circular,
            'orphan_modules': orphans,
            'hotspots': hotspots
        },
        'caveat': 'Static analysis only. Dynamic imports, plugins, and external consumers not detected.'
    }


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Analyze codebase structure and dependencies')
    parser.add_argument('directory', nargs='?', default='.', help='Directory to analyze')
    parser.add_argument('--mode', choices=['stats', 'deps', 'full'], default='full',
                        help='Analysis mode: stats (file metrics), deps (dependency graph), full (both)')

    args = parser.parse_args()

    if args.mode == 'stats':
        result = analyze_directory_stats(args.directory)
    elif args.mode == 'deps':
        result = analyze_directory_deps(args.directory)
    else:  # full
        stats = analyze_directory_stats(args.directory)
        deps = analyze_directory_deps(args.directory)

        if 'error' in stats and 'error' in deps:
            result = {'error': stats['error'], 'directory': args.directory}
        elif 'error' in deps:
            result = {'stats': stats, 'deps': {'note': deps.get('error', 'No Python files for dependency analysis')}}
        elif 'error' in stats:
            result = {'stats': {'note': stats.get('error', 'No source files found')}, 'deps': deps}
        else:
            result = {'stats': stats, 'deps': deps}

    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
