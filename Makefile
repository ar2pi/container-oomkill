up:
	docker compose up --build

probe:
	@docker build -q -t ar2pi/container-oomkill-probe . > /dev/null
	@docker run --privileged --pid=host -v /sys:/sys:ro ar2pi/container-oomkill-probe

exporter:
	@docker build -q -t ar2pi/container-oomkill-exporter -f Dockerfile.exporter . > /dev/null
	@docker run --privileged --pid=host -v /sys:/sys:ro -p 9262:9262 ar2pi/container-oomkill-exporter

build:
	docker build -t ar2pi/container-oomkill-probe .
	docker build -t ar2pi/container-oomkill-exporter -f Dockerfile.exporter .

push: build
	docker push ar2pi/container-oomkill-probe
	docker push ar2pi/container-oomkill-exporter

clean:
	docker system prune -a
