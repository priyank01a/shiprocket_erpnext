from setuptools import find_packages, setup


with open("README.md", encoding="utf-8") as readme:
    long_description = readme.read()


setup(
    name="shiprocket_erpnext",
    version="0.1.0",
    description="ERPNext Delivery Note to Shiprocket integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Codex",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["requests>=2.25.0"],
)

