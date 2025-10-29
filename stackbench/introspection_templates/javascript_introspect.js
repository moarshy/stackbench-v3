#!/usr/bin/env node
/**
 * JavaScript/TypeScript Library Introspection Script - Language-agnostic output format.
 *
 * This script introspects a JavaScript/TypeScript library and outputs a standardized JSON format
 * that works across all languages (Python, JavaScript, TypeScript, etc.).
 *
 * Usage:
 *     node javascript_introspect.js <library_name> <version> [modules...]
 *
 * Output (stdout):
 *     {
 *       "library": "express",
 *       "version": "4.18.2",
 *       "language": "javascript",
 *       "total_apis": 42,
 *       "apis": [...],
 *       "by_type": {...}
 *     }
 */

const fs = require('fs');
const path = require('path');

/**
 * Check if an API is deprecated.
 */
function isDeprecated(obj, name) {
    if (obj && obj.deprecated) return true;

    // Check JSDoc comments
    const docString = obj?.toString() || '';
    if (docString.includes('@deprecated') || docString.includes('deprecated')) return true;

    return false;
}

/**
 * Check if a function is async.
 */
function isAsync(fn) {
    return fn?.constructor?.name === 'AsyncFunction';
}

/**
 * Extract function signature.
 */
function getSignature(fn, name) {
    if (!fn) return '';

    try {
        const fnStr = fn.toString();
        const match = fnStr.match(/^(async\s+)?function\s*\w*\s*\((.*?)\)/);
        if (match) {
            return `(${match[2]})`;
        }

        // Arrow function or method
        const arrowMatch = fnStr.match(/^(async\s*)?\((.*?)\)\s*=>/);
        if (arrowMatch) {
            return `(${arrowMatch[2]})`;
        }

        // Method
        const methodMatch = fnStr.match(/^\w+\s*\((.*?)\)/);
        if (methodMatch) {
            return `(${methodMatch[1]})`;
        }

        return `(${fn.length} params)`;
    } catch (e) {
        return `(${fn.length} params)`;
    }
}

/**
 * Check if object has documentation (JSDoc).
 */
function hasDocstring(obj) {
    if (!obj) return false;

    const objStr = obj.toString();
    return objStr.includes('/**') || objStr.includes('//');
}

/**
 * Introspect a module/object recursively.
 */
function introspectModule(obj, moduleName, parentPath = '', depth = 0, maxDepth = 3, exportedNames = null) {
    const apis = [];

    if (depth > maxDepth || !obj || typeof obj !== 'object') {
        return apis;
    }

    const seen = new Set();

    // Get all property names (including non-enumerable)
    const allNames = new Set([
        ...Object.keys(obj),
        ...Object.getOwnPropertyNames(obj)
    ]);

    for (const name of allNames) {
        // Skip private members (starting with _)
        if (name.startsWith('_')) continue;

        // Skip common Node.js internal properties
        if (['constructor', 'prototype', '__proto__', 'length', 'name', 'arguments', 'caller'].includes(name)) continue;

        try {
            const member = obj[name];
            if (!member) continue;

            // Avoid circular references
            const memberId = `${parentPath}.${name}`;
            if (seen.has(memberId)) continue;
            seen.add(memberId);

            const fullName = parentPath ? `${parentPath}.${name}` : name;
            const inExports = exportedNames ? exportedNames.has(name) : true;

            const memberType = typeof member;

            // Handle functions
            if (memberType === 'function') {
                // Distinguish between class and function
                const isClass = member.toString().startsWith('class ');

                if (isClass) {
                    // Add class
                    apis.push({
                        api: fullName,
                        module: moduleName,
                        type: 'class',
                        is_async: false,
                        has_docstring: hasDocstring(member),
                        in_all: inExports,
                        is_deprecated: isDeprecated(member, name),
                        signature: `class ${name}`
                    });

                    // Add class methods
                    const proto = member.prototype;
                    if (proto) {
                        const methodNames = Object.getOwnPropertyNames(proto);
                        for (const methodName of methodNames) {
                            if (methodName === 'constructor' || methodName.startsWith('_')) continue;

                            try {
                                const method = proto[methodName];
                                if (typeof method === 'function') {
                                    apis.push({
                                        api: `${fullName}.${methodName}`,
                                        module: moduleName,
                                        type: 'method',
                                        is_async: isAsync(method),
                                        has_docstring: hasDocstring(method),
                                        in_all: false,
                                        is_deprecated: isDeprecated(method, methodName),
                                        signature: getSignature(method, methodName)
                                    });
                                }
                            } catch (e) {
                                // Skip inaccessible methods
                            }
                        }
                    }

                    // Add static methods
                    const staticNames = Object.getOwnPropertyNames(member);
                    for (const staticName of staticNames) {
                        if (['length', 'name', 'prototype'].includes(staticName) || staticName.startsWith('_')) continue;

                        try {
                            const staticMember = member[staticName];
                            if (typeof staticMember === 'function') {
                                apis.push({
                                    api: `${fullName}.${staticName}`,
                                    module: moduleName,
                                    type: 'method',
                                    is_async: isAsync(staticMember),
                                    has_docstring: hasDocstring(staticMember),
                                    in_all: false,
                                    is_deprecated: isDeprecated(staticMember, staticName),
                                    signature: getSignature(staticMember, staticName)
                                });
                            }
                        } catch (e) {
                            // Skip inaccessible static members
                        }
                    }
                } else {
                    // Regular function
                    apis.push({
                        api: fullName,
                        module: moduleName,
                        type: 'function',
                        is_async: isAsync(member),
                        has_docstring: hasDocstring(member),
                        in_all: inExports,
                        is_deprecated: isDeprecated(member, name),
                        signature: getSignature(member, name)
                    });
                }
            }
            // Handle nested objects (sub-modules)
            else if (memberType === 'object' && !Array.isArray(member) && depth < maxDepth) {
                const subApis = introspectModule(member, moduleName, fullName, depth + 1, maxDepth, null);
                apis.push(...subApis);
            }
        } catch (e) {
            // Skip inaccessible members
            continue;
        }
    }

    return apis;
}

/**
 * Main introspection logic.
 */
function main() {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('Usage: node javascript_introspect.js <library_name> <version> [modules...]');
        process.exit(1);
    }

    const libraryName = args[0];
    const version = args[1];
    const modules = args.length > 2 ? args.slice(2) : [libraryName];

    let allApis = [];

    for (const moduleName of modules) {
        try {
            // Try to require the module
            const module = require(moduleName);

            // Get exported names
            const exportedNames = new Set(Object.keys(module));

            // Introspect the module
            const apis = introspectModule(module, moduleName, moduleName, 0, 3, exportedNames);
            allApis.push(...apis);
        } catch (e) {
            console.error(`ERROR: Failed to import ${moduleName}: ${e.message}`, file=process.stderr);
            continue;
        }
    }

    // Group by type
    const byType = {};
    for (const api of allApis) {
        const apiType = api.type;
        byType[apiType] = (byType[apiType] || 0) + 1;
    }

    // Build standardized output
    const output = {
        library: libraryName,
        version: version,
        language: 'javascript',
        total_apis: allApis.length,
        apis: allApis,
        by_type: byType,
        deprecated_count: allApis.filter(a => a.is_deprecated).length
    };

    // Output JSON to stdout
    console.log(JSON.stringify(output, null, 2));
}

if (require.main === module) {
    main();
}
