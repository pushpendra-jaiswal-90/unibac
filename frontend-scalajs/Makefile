.PHONY: build serve clean

build:
	sbt fastLinkJS

serve: build
	@echo "Open http://localhost:5173 in your browser."
	python3 -m http.server 5173

clean:
	sbt clean
