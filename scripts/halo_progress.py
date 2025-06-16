#!/usr/bin/env python3
"""
Simple halo progress utility for bash scripts.
No configuration needed - just uses halo spinners.
"""

import sys
import time
import argparse
from halo import Halo


def spinner(message: str, duration: float = 2.0):
    """Show a spinner for a specified duration."""
    with Halo(text=message, spinner='dots', color='cyan') as spinner:
        time.sleep(duration)
        spinner.succeed(f"{message} - done")


def success(message: str):
    """Show success message."""
    Halo(text=message, spinner='dots', color='green').succeed()


def error(message: str):
    """Show error message."""
    Halo(text=message, spinner='dots', color='red').fail()


def info(message: str):
    """Show info message."""
    Halo(text=message, spinner='dots', color='blue').info()


def main():
    parser = argparse.ArgumentParser(description='Halo progress utility')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Spinner command
    spinner_parser = subparsers.add_parser('spinner', help='Show a spinner')
    spinner_parser.add_argument('message', help='Message to display')
    spinner_parser.add_argument('duration', type=float, nargs='?', default=2.0,
                               help='Duration in seconds')
    
    # Status commands
    for cmd in ['success', 'error', 'info']:
        cmd_parser = subparsers.add_parser(cmd, help=f'Show {cmd} message')
        cmd_parser.add_argument('message', help='Message to display')
    
    args = parser.parse_args()
    
    if args.command == 'spinner':
        spinner(args.message, args.duration)
    elif args.command == 'success':
        success(args.message)
    elif args.command == 'error':
        error(args.message)
    elif args.command == 'info':
        info(args.message)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()