.PHONY: build serve clean

build:
	elm make src/Main.elm --output=app.js

serve: build
	@echo "Open http://localhost:5174 in your browser."
	python3 -m http.server 5174

clean:
	rm -rf elm-stuff app.js
