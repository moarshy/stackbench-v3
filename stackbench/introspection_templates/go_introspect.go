#!/usr/bin/env go run
/**
 * Go Library Introspection Script - Language-agnostic output format.
 *
 * This script introspects a Go module and outputs a standardized JSON format
 * that works across all languages (Python, JavaScript, TypeScript, Go, Rust).
 *
 * Uses go/parser and go/ast to extract exported symbols.
 *
 * Usage:
 *     go run go_introspect.go <module_name> <version> [packages...]
 *
 * Output (stdout):
 *     {
 *       "library": "github.com/user/lib",
 *       "version": "v1.0.0",
 *       "language": "go",
 *       "total_apis": 42,
 *       "apis": [...],
 *       "by_type": {...}
 *     }
 */

package main

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
)

// APIMetadata represents a single API in standardized format
type APIMetadata struct {
	API           string `json:"api"`
	Module        string `json:"module"`
	Type          string `json:"type"` // function, class, method, property
	IsAsync       bool   `json:"is_async"`
	HasDocstring  bool   `json:"has_docstring"`
	InAll         bool   `json:"in_all"` // Exported (capitalized in Go)
	IsDeprecated  bool   `json:"is_deprecated"`
	Signature     string `json:"signature"`
}

// IntrospectionOutput represents the complete output
type IntrospectionOutput struct {
	Library         string                   `json:"library"`
	Version         string                   `json:"version"`
	Language        string                   `json:"language"`
	TotalAPIs       int                      `json:"total_apis"`
	APIs            []APIMetadata            `json:"apis"`
	ByType          map[string]int           `json:"by_type"`
	DeprecatedCount int                      `json:"deprecated_count"`
}

// isExported checks if an identifier is exported (starts with uppercase)
func isExported(name string) bool {
	if len(name) == 0 {
		return false
	}
	return name[0] >= 'A' && name[0] <= 'Z'
}

// isDeprecated checks if documentation indicates deprecation
func isDeprecated(doc *ast.CommentGroup) bool {
	if doc == nil {
		return false
	}
	text := doc.Text()
	return strings.Contains(strings.ToLower(text), "deprecated")
}

// hasDocstring checks if symbol has documentation
func hasDocstring(doc *ast.CommentGroup) bool {
	return doc != nil && len(doc.List) > 0
}

// getSignature extracts function signature as string
func getSignature(funcType *ast.FuncType) string {
	if funcType == nil {
		return ""
	}

	var params []string
	if funcType.Params != nil {
		for _, field := range funcType.Params.List {
			// Get parameter type as string
			typeStr := fmt.Sprintf("%v", field.Type)
			if len(field.Names) > 0 {
				for _, name := range field.Names {
					params = append(params, fmt.Sprintf("%s %s", name.Name, typeStr))
				}
			} else {
				params = append(params, typeStr)
			}
		}
	}

	var results []string
	if funcType.Results != nil {
		for _, field := range funcType.Results.List {
			typeStr := fmt.Sprintf("%v", field.Type)
			results = append(results, typeStr)
		}
	}

	sig := fmt.Sprintf("(%s)", strings.Join(params, ", "))
	if len(results) > 0 {
		sig += fmt.Sprintf(" (%s)", strings.Join(results, ", "))
	}

	return sig
}

// introspectPackage introspects a single Go package
func introspectPackage(pkgPath string, moduleName string) ([]APIMetadata, error) {
	var apis []APIMetadata

	fset := token.NewFileSet()
	pkgs, err := parser.ParseDir(fset, pkgPath, nil, parser.ParseComments)
	if err != nil {
		return nil, err
	}

	for pkgName, pkg := range pkgs {
		// Skip test packages
		if strings.HasSuffix(pkgName, "_test") {
			continue
		}

		for _, file := range pkg.Files {
			for _, decl := range file.Decls {
				switch d := decl.(type) {
				case *ast.FuncDecl:
					// Function or method
					if !isExported(d.Name.Name) {
						continue
					}

					apiType := "function"
					apiName := d.Name.Name

					// Check if it's a method (has receiver)
					if d.Recv != nil {
						apiType = "method"
						// Try to get receiver type name
						if len(d.Recv.List) > 0 {
							recvType := fmt.Sprintf("%v", d.Recv.List[0].Type)
							// Clean up pointer syntax
							recvType = strings.TrimPrefix(recvType, "*")
							apiName = fmt.Sprintf("%s.%s", recvType, d.Name.Name)
						}
					}

					apis = append(apis, APIMetadata{
						API:          fmt.Sprintf("%s.%s", pkgName, apiName),
						Module:       moduleName,
						Type:         apiType,
						IsAsync:      false, // Go doesn't have async/await
						HasDocstring: hasDocstring(d.Doc),
						InAll:        true, // Exported
						IsDeprecated: isDeprecated(d.Doc),
						Signature:    getSignature(d.Type),
					})

				case *ast.GenDecl:
					// Type, const, var declarations
					for _, spec := range d.Specs {
						switch s := spec.(type) {
						case *ast.TypeSpec:
							// Type declaration (struct, interface, etc.)
							if !isExported(s.Name.Name) {
								continue
							}

							apiType := "class" // Use "class" for consistency with other languages

							// Check if it's a struct
							if _, ok := s.Type.(*ast.StructType); ok {
								apiType = "class"
							}

							apis = append(apis, APIMetadata{
								API:          fmt.Sprintf("%s.%s", pkgName, s.Name.Name),
								Module:       moduleName,
								Type:         apiType,
								IsAsync:      false,
								HasDocstring: hasDocstring(d.Doc),
								InAll:        true,
								IsDeprecated: isDeprecated(d.Doc),
								Signature:    fmt.Sprintf("type %s", s.Name.Name),
							})
						}
					}
				}
			}
		}
	}

	return apis, nil
}

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintln(os.Stderr, "Usage: go run go_introspect.go <module_name> <version> [packages...]")
		os.Exit(1)
	}

	moduleName := os.Args[1]
	version := os.Args[2]
	packages := os.Args[3:]

	if len(packages) == 0 {
		// Default to current directory
		packages = []string{"."}
	}

	var allAPIs []APIMetadata
	byType := make(map[string]int)

	for _, pkgPath := range packages {
		apis, err := introspectPackage(pkgPath, moduleName)
		if err != nil {
			fmt.Fprintf(os.Stderr, "ERROR: Failed to introspect package %s: %v\n", pkgPath, err)
			continue
		}

		allAPIs = append(allAPIs, apis...)
	}

	// Count by type
	deprecatedCount := 0
	for _, api := range allAPIs {
		byType[api.Type]++
		if api.IsDeprecated {
			deprecatedCount++
		}
	}

	// Build output
	output := IntrospectionOutput{
		Library:         moduleName,
		Version:         version,
		Language:        "go",
		TotalAPIs:       len(allAPIs),
		APIs:            allAPIs,
		ByType:          byType,
		DeprecatedCount: deprecatedCount,
	}

	// Output JSON to stdout
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(output); err != nil {
		fmt.Fprintf(os.Stderr, "ERROR: Failed to encode JSON: %v\n", err)
		os.Exit(1)
	}
}
