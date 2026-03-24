from setuptools import setup, find_packages

setup(
    name="loq-control",
    version="0.8.0",
    packages=find_packages(),
    install_requires=[
        "psutil>=5.9.0",
        "PyGObject>=3.42.0",
    ],
    entry_points={
        "console_scripts": [
            "loq-control=loq_control.cli:main",
            "loq-daemon=loq_control.services.daemon:main",
            "loq-gui=loq_control.gui.main:main",
            "loq-report=loq_control.tools.stability_report:main",
        ],
    },
    author="Vaibhav Pandit",
    description="Advanced Hardware Control for Lenovo LOQ Laptops",
    python_requires=">=3.8",
)
