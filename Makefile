prefix	?= $(HOME)
PYTHON	?= python
PYTHON_VER	?= $(shell $(PYTHON) -c 'import platform; print(platform.python_version()[:3])')
PYTHON_LIB	?= $(shell $(PYTHON) -c 'import os.path as p; import distutils.sysconfig as sc; print(p.basename(sc.get_config_var("LIBDIR")))')
PYTHON_SITE	?= $(DESTDIR)$(prefix)/$(PYTHON_LIB)/python$(PYTHON_VER)/site-packages
COLA_VERSION	?= $(shell git describe --match='v*.*' | sed -e s/v//)
APP	?= git-cola.app
TAR	?= tar
TEST_PYTHONPATH	?= "$(CURDIR)":"$(CURDIR)/thirdparty":"$(PYTHONPATH)"

# User customizations
-include config.mak

ifdef standalone
standalone_args	?= --standalone
endif

all:
	$(PYTHON) setup.py build

git-cola.app:
	mkdir -p $(APP)/Contents/MacOS
	cp darwin/git-cola $(APP)/Contents/MacOS
	cp darwin/Info.plist darwin/PkgInfo $(APP)/Contents
	$(MAKE) prefix=$(APP)/Contents/Resources install
	cp darwin/git-cola.icns $(APP)/Contents/Resources
	$(TAR) czf $(APP)-$(COLA_VERSION).tar.gz $(APP)

install: all
	$(PYTHON) setup.py --quiet install \
		$(standalone_args) \
		--install-scripts=$(DESTDIR)$(prefix)/bin \
		--prefix=$(DESTDIR)$(prefix) \
		--force && \
	rm -f $(PYTHON_SITE)/git_cola*
	rmdir -p $(PYTHON_SITE) 2>/dev/null || true
	(cd $(DESTDIR)$(prefix)/bin && \
	! test -e cola && ln -s git-cola cola) || true

# Maintainer's dist target
COLA_TARNAME ?= cola-$(COLA_VERSION)
dist: all
	git archive --format=tar \
		--prefix=$(COLA_TARNAME)/ HEAD^{tree} > $(COLA_TARNAME).tar
	@mkdir -p $(COLA_TARNAME)/cola
	@cp cola/builtin_version.py $(COLA_TARNAME)/cola
	@cp cola/builtin_version.py $(COLA_TARNAME)/version
	$(TAR) rf $(COLA_TARNAME).tar \
		$(COLA_TARNAME)/version \
		$(COLA_TARNAME)/cola/builtin_version.py
	@$(RM) -r $(COLA_TARNAME)
	gzip -f -9 $(COLA_TARNAME).tar

doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) all

html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) html

install-doc:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install

install-html:
	$(MAKE) -C share/doc/git-cola prefix=$(prefix) install-html

uninstall:
	rm -rf  $(DESTDIR)$(prefix)/bin/git-cola \
		$(DESTDIR)$(prefix)/bin/cola \
		$(DESTDIR)$(prefix)/share/applications/cola.desktop \
		$(DESTDIR)$(prefix)/share/git-cola \
		$(DESTDIR)$(prefix)/share/doc/git-cola

test_flags	:=
all_test_flags	?= --with-doctest $(test_flags)

test: all
	@env PYTHONPATH="$(TEST_PYTHONPATH)" \
	nosetests $(all_test_flags)

coverage:
	@env PYTHONPATH="$(TEST_PYTHONPATH)" \
	nosetests --with-coverage --cover-package=cola $(all_test_flags)

clean:
	$(MAKE) -C share/doc/git-cola clean
	find . -name .noseids -print0 | xargs -0 rm -f
	find . -name '*.py[co]' -print0 | xargs -0 rm -f
	rm -rf cola/builtin_version.* build dist tmp tags git-cola.app
	rm -rf share/locale

tags:
	ctags cola/*.py cola/*/*.py test/*.py

pot:
	$(PYTHON) setup.py build_pot -N -d .

mo:
	$(PYTHON) setup.py build_mo -f

.PHONY: all install doc install-doc install-html test clean tags git-cola.app
