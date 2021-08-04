PACKAGE := juicefs
VERSION := $(shell cat juicefs/version.py | sed -n -E 's/^VERSION = "(.+?)"/\1/p')
JUICEFS_VERSION := 0.14.2

clean:
	rm -rf dist build *.egg-info .pytype .pytest_cache .pytype_output

build_juicefs:
	rm -rf build && mkdir build
	cd build \
		&& wget https://github.com/juicedata/juicefs/releases/download/v${JUICEFS_VERSION}/juicefs-${JUICEFS_VERSION}-linux-amd64.tar.gz \
		&& tar -zxf juicefs-${JUICEFS_VERSION}-linux-amd64.tar.gz \
		&& cp juicefs ../juicefs/lib/juicefs

build_libjfs:
	rm -rf build && mkdir build
	cd build \
		&& wget https://github.com/juicedata/juicefs/archive/refs/tags/v${JUICEFS_VERSION}.zip \
		&& unzip v${JUICEFS_VERSION}.zip \
		&& cd juicefs-${JUICEFS_VERSION}/sdk/java/libjfs \
		&& make libjfs.so \
		&& cp libjfs.so ../../../../../juicefs/lib/libjfs.so

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
	git tag ${VERSION}
	git push origin ${VERSION}

	rm -rf build dist
	python3 setup.py bdist

	devpi login ${PYPI_USERNAME} --password=${PYPI_PASSWORD}
	devpi upload dist/${PACKAGE}-${VERSION}.linux-x86_64.tar.gz
