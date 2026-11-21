// Render module configFiles using the operator's standard text/template context.
// This helper has no module-specific substitutions or template functions.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"text/template"
)

func main() {
	var input struct {
		Files  []struct{ Path, Template string }
		Values map[string]string
		Server struct{ Name, Namespace string }
	}
	if err := json.NewDecoder(os.Stdin).Decode(&input); err != nil {
		panic(err)
	}
	output := make(map[string]string)
	for _, file := range input.Files {
		t, err := template.New(file.Path).Option("missingkey=error").Parse(file.Template)
		if err != nil {
			panic(err)
		}
		var buffer bytes.Buffer
		if err := t.Execute(&buffer, input); err != nil {
			panic(err)
		}
		output[file.Path] = buffer.String()
	}
	if err := json.NewEncoder(os.Stdout).Encode(output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
