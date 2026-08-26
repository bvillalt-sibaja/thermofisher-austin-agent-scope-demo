#!/usr/bin/env python3
"""Entry point for the Thermo Fisher SAP GUI mirror demo app.

Run: python3 main.py
"""
from sap_app.app import launch


def main():
    root, session = launch()
    root.mainloop()


if __name__ == "__main__":
    main()
