import setuptools
from pathlib import Path

README = Path("./README.md").read_text()
REQUIREMENTS = Path("./requirements.txt").read_text().split()
REPO_URL = "https://github.com/yoogottamk/clipstack"


setuptools.setup(
    name="clipstack",
    version="0.0.1",
    author="Yoogottam Khandelwal",
    author_email="yoogottamk@outlook.com",
    description="A highly configurable stack-based clipboard manager",
    long_description=README,
    long_description_content_type="text/markdown",
    url=REPO_URL,
    project_urls={
        "Bug Tracker": f"{REPO_URL}/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Linux",
    ],
    packages=setuptools.find_packages(exclude=[".demos"]),
    python_requires=">=3.6",
    install_requires=REQUIREMENTS,
)
