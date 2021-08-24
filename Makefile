PACKAGE := juicefs
VERSION := $(shell cat juicefs/version.py | sed -n -E 's/^VERSION = "(.+?)"/\1/p')
JUICEFS_VERSION := 0.14.2

clean:
	rm -rf dist build *.egg-info .pytype .pytest_cache .pytype_output

build_libjfs_linux:
	rm -rf build && mkdir build
	cd build \
		&& wget https://github.com/juicedata/juicefs/archive/refs/tags/v${JUICEFS_VERSION}.zip \
		&& unzip v${JUICEFS_VERSION}.zip
	cd build/juicefs-${JUICEFS_VERSION}/sdk/java/libjfs \
		&& make libjfs.so \
		&& cp libjfs.so ../../../../../juicefs/lib/libjfs.so
	cd build/juicefs-${JUICEFS_VERSION} \
		&& make juicefs \
		&& cp juicefs ../../juicefs/lib/juicefs

build_libjfs_win:
	rm -rf build && mkdir build
	cd build \
		&& wget https://github.com/juicedata/juicefs/archive/refs/tags/v${JUICEFS_VERSION}.zip \
		&& unzip v${JUICEFS_VERSION}.zip
	cd build/juicefs-${JUICEFS_VERSION}/sdk/java/libjfs \
		&& make libjfs.dll \
		&& cp libjfs.dll ../../../../../juicefs/lib/libjfs.dll
	cd build/juicefs-${JUICEFS_VERSION} \
		&& make juicefs.exe \
		&& cp juicefs.exe ../../juicefs/lib/juicefs.exe

print_libjfs_version:
	echo ${JUICEFS_VERSION}

build_wheel:
	python3 setup.py bdist_wheel

static_check:
	pytype ${PACKAGE}

test:
	pytest -s --cov=${PACKAGE} --no-cov-on-fail --cov-report=html:html_cov/ --cov-report=term-missing tests

style_check:
	isort --check --diff ${PACKAGE}
	black --check --diff ${PACKAGE}

format:
	autoflake --remove-unused-variables --remove-all-unused-imports --ignore-init-module-imports -r -i ${PACKAGE} tests
	isort ${PACKAGE} tests
	black ${PACKAGE} tests

doc:
	python3 setup.py build_sphinx --fresh-env --build-dir html_doc/

release:
	# git tag ${VERSION}
	# git push origin ${VERSION}

	rm -rf build dist
	python3 setup.py bdist_wheel
	auditwheel repair --plat manylinux2014_x86_64 dist/${PACKAGE}-${VERSION}-py3-none-any.whl

	devpi login ${PYPI_USERNAME} --password=${PYPI_PASSWORD}
	devpi upload wheelhouse/${PACKAGE}-${VERSION}-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
	twine upload wheelhouse/${PACKAGE}-${VERSION}-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl --username=${PYPI_USERNAME_2} --password=${PYPI_PASSWORD_2}
