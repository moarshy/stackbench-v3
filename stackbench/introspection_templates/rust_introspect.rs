#!/usr/bin/env cargo +nightly -Zscript
```cargo
[dependencies]
syn = { version = "2.0", features = ["full", "visit"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```
/**
 * Rust Crate Introspection Script - Language-agnostic output format.
 *
 * This script introspects a Rust crate and outputs a standardized JSON format
 * that works across all languages (Python, JavaScript, TypeScript, Go, Rust).
 *
 * Uses syn crate to parse Rust source and extract public items.
 *
 * Usage:
 *     cargo +nightly -Zscript rust_introspect.rs <crate_name> <version> [modules...]
 *     OR
 *     rustc rust_introspect.rs && ./rust_introspect <crate_name> <version>
 *
 * Output (stdout):
 *     {
 *       "library": "serde",
 *       "version": "1.0.0",
 *       "language": "rust",
 *       "total_apis": 42,
 *       "apis": [...],
 *       "by_type": {...}
 *     }
 */

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::Path;
use syn::visit::Visit;
use syn::{Item, ItemFn, ItemMod, ItemStruct, ItemEnum, ItemTrait, Visibility};

#[derive(Debug, Serialize, Deserialize)]
struct APIMetadata {
    api: String,
    module: String,
    #[serde(rename = "type")]
    api_type: String, // function, class, method, property
    is_async: bool,
    has_docstring: bool,
    in_all: bool, // pub (public visibility)
    is_deprecated: bool,
    signature: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct IntrospectionOutput {
    library: String,
    version: String,
    language: String,
    total_apis: usize,
    apis: Vec<APIMetadata>,
    by_type: HashMap<String, usize>,
    deprecated_count: usize,
}

/// Check if item is public
fn is_public(vis: &Visibility) -> bool {
    matches!(vis, Visibility::Public(_))
}

/// Check if documentation contains deprecation notice
fn is_deprecated(attrs: &[syn::Attribute]) -> bool {
    attrs.iter().any(|attr| {
        if attr.path().is_ident("deprecated") {
            return true;
        }
        if let Ok(meta) = attr.parse_meta() {
            if let syn::Meta::NameValue(nv) = meta {
                if let syn::Lit::Str(s) = &nv.lit {
                    return s.value().to_lowercase().contains("deprecated");
                }
            }
        }
        false
    })
}

/// Check if item has documentation
fn has_docstring(attrs: &[syn::Attribute]) -> bool {
    attrs.iter().any(|attr| {
        attr.path().is_ident("doc")
    })
}

/// Extract function signature
fn get_fn_signature(sig: &syn::Signature) -> String {
    let inputs: Vec<String> = sig.inputs.iter().map(|arg| {
        match arg {
            syn::FnArg::Receiver(_) => "self".to_string(),
            syn::FnArg::Typed(pat_type) => {
                format!("{}: {}", quote::quote!(#pat_type.pat), quote::quote!(#pat_type.ty))
            }
        }
    }).collect();

    let output = match &sig.output {
        syn::ReturnType::Default => String::new(),
        syn::ReturnType::Type(_, ty) => format!(" -> {}", quote::quote!(#ty)),
    };

    format!("({}){}", inputs.join(", "), output)
}

/// Visitor to collect public APIs
struct APICollector {
    apis: Vec<APIMetadata>,
    module_path: Vec<String>,
    crate_name: String,
}

impl APICollector {
    fn new(crate_name: String) -> Self {
        Self {
            apis: Vec::new(),
            module_path: vec![crate_name.clone()],
            crate_name,
        }
    }

    fn current_module(&self) -> String {
        self.module_path.join("::")
    }

    fn add_api(&mut self, metadata: APIMetadata) {
        self.apis.push(metadata);
    }
}

impl<'ast> Visit<'ast> for APICollector {
    fn visit_item_fn(&mut self, node: &'ast ItemFn) {
        if is_public(&node.vis) {
            let api_name = node.sig.ident.to_string();
            let full_name = format!("{}::{}", self.current_module(), api_name);

            self.add_api(APIMetadata {
                api: full_name,
                module: self.current_module(),
                api_type: "function".to_string(),
                is_async: node.sig.asyncness.is_some(),
                has_docstring: has_docstring(&node.attrs),
                in_all: true,
                is_deprecated: is_deprecated(&node.attrs),
                signature: get_fn_signature(&node.sig),
            });
        }

        // Continue visiting nested items
        syn::visit::visit_item_fn(self, node);
    }

    fn visit_item_struct(&mut self, node: &'ast ItemStruct) {
        if is_public(&node.vis) {
            let struct_name = node.ident.to_string();
            let full_name = format!("{}::{}", self.current_module(), struct_name);

            self.add_api(APIMetadata {
                api: full_name,
                module: self.current_module(),
                api_type: "class".to_string(), // Use "class" for consistency
                is_async: false,
                has_docstring: has_docstring(&node.attrs),
                in_all: true,
                is_deprecated: is_deprecated(&node.attrs),
                signature: format!("struct {}", struct_name),
            });
        }

        syn::visit::visit_item_struct(self, node);
    }

    fn visit_item_enum(&mut self, node: &'ast ItemEnum) {
        if is_public(&node.vis) {
            let enum_name = node.ident.to_string();
            let full_name = format!("{}::{}", self.current_module(), enum_name);

            self.add_api(APIMetadata {
                api: full_name,
                module: self.current_module(),
                api_type: "class".to_string(),
                is_async: false,
                has_docstring: has_docstring(&node.attrs),
                in_all: true,
                is_deprecated: is_deprecated(&node.attrs),
                signature: format!("enum {}", enum_name),
            });
        }

        syn::visit::visit_item_enum(self, node);
    }

    fn visit_item_trait(&mut self, node: &'ast ItemTrait) {
        if is_public(&node.vis) {
            let trait_name = node.ident.to_string();
            let full_name = format!("{}::{}", self.current_module(), trait_name);

            self.add_api(APIMetadata {
                api: full_name,
                module: self.current_module(),
                api_type: "class".to_string(),
                is_async: false,
                has_docstring: has_docstring(&node.attrs),
                in_all: true,
                is_deprecated: is_deprecated(&node.attrs),
                signature: format!("trait {}", trait_name),
            });

            // Also collect trait methods
            for item in &node.items {
                if let syn::TraitItem::Method(method) = item {
                    let method_name = method.sig.ident.to_string();
                    let method_full_name = format!("{}::{}", full_name, method_name);

                    self.add_api(APIMetadata {
                        api: method_full_name,
                        module: self.current_module(),
                        api_type: "method".to_string(),
                        is_async: method.sig.asyncness.is_some(),
                        has_docstring: has_docstring(&method.attrs),
                        in_all: true,
                        is_deprecated: is_deprecated(&method.attrs),
                        signature: get_fn_signature(&method.sig),
                    });
                }
            }
        }

        syn::visit::visit_item_trait(self, node);
    }

    fn visit_item_mod(&mut self, node: &'ast ItemMod) {
        if is_public(&node.vis) {
            // Enter module
            self.module_path.push(node.ident.to_string());

            // Visit module contents
            if let Some((_, items)) = &node.content {
                for item in items {
                    self.visit_item(item);
                }
            }

            // Exit module
            self.module_path.pop();
        }
    }
}

fn introspect_file(file_path: &Path, crate_name: &str) -> Result<Vec<APIMetadata>, Box<dyn std::error::Error>> {
    let code = fs::read_to_string(file_path)?;
    let syntax_tree = syn::parse_file(&code)?;

    let mut collector = APICollector::new(crate_name.to_string());
    collector.visit_file(&syntax_tree);

    Ok(collector.apis)
}

fn main() {
    let args: Vec<String> = env::args().collect();

    if args.len() < 3 {
        eprintln!("Usage: {} <crate_name> <version> [source_files...]", args[0]);
        std::process::exit(1);
    }

    let crate_name = &args[1];
    let version = &args[2];
    let source_files: Vec<&String> = args.get(3..).unwrap_or(&[]).iter().collect();

    let mut all_apis = Vec::new();

    // If no source files specified, try to find src/lib.rs or src/main.rs
    let files_to_process: Vec<String> = if source_files.is_empty() {
        vec!["src/lib.rs".to_string(), "src/main.rs".to_string()]
    } else {
        source_files.iter().map(|s| s.to_string()).collect()
    };

    for file_path_str in files_to_process {
        let file_path = Path::new(&file_path_str);
        if !file_path.exists() {
            continue;
        }

        match introspect_file(file_path, crate_name) {
            Ok(apis) => all_apis.extend(apis),
            Err(e) => eprintln!("ERROR: Failed to introspect {}: {}", file_path_str, e),
        }
    }

    // Count by type
    let mut by_type: HashMap<String, usize> = HashMap::new();
    let mut deprecated_count = 0;

    for api in &all_apis {
        *by_type.entry(api.api_type.clone()).or_insert(0) += 1;
        if api.is_deprecated {
            deprecated_count += 1;
        }
    }

    // Build output
    let output = IntrospectionOutput {
        library: crate_name.to_string(),
        version: version.to_string(),
        language: "rust".to_string(),
        total_apis: all_apis.len(),
        apis: all_apis,
        by_type,
        deprecated_count,
    };

    // Output JSON to stdout
    match serde_json::to_string_pretty(&output) {
        Ok(json) => println!("{}", json),
        Err(e) => {
            eprintln!("ERROR: Failed to serialize JSON: {}", e);
            std::process::exit(1);
        }
    }
}
