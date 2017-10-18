all:

site:
	@ansible-playbook site.yml

bootstrap:
	@ansible-playbook --ask-pass bootstrap.yml

clean:
	@rm -f *.retry log

.PHONY: all site bootstrap clean
