#!/usr/bin/env ts-node
/**
 * TypeScript Library Introspection Script - Language-agnostic output format.
 *
 * This script introspects a TypeScript library and outputs a standardized JSON format
 * that works across all languages (Python, JavaScript, TypeScript, etc.).
 *
 * This uses the TypeScript Compiler API to extract type information when available.
 *
 * Usage:
 *     ts-node typescript_introspect.ts <library_name> <version> [modules...]
 *
 * Output (stdout):
 *     {
 *       "library": "express",
 *       "version": "4.18.2",
 *       "language": "typescript",
 *       "total_apis": 42,
 *       "apis": [...],
 *       "by_type": {...}
 *     }
 */

interface APIMetadata {
    api: string;
    module: string;
    type: 'function' | 'class' | 'method' | 'property';
    is_async: boolean;
    has_docstring: boolean;
    in_all: boolean;
    is_deprecated: boolean;
    signature: string;
}

interface IntrospectionOutput {
    library: string;
    version: string;
    language: string;
    total_apis: number;
    apis: APIMetadata[];
    by_type: Record<string, number>;
    deprecated_count: number;
}

/**
 * Check if an API is deprecated.
 */
function isDeprecated(obj: any, name: string): boolean {
    if (obj && obj.deprecated) return true;

    const docString = obj?.toString() || '';
    if (docString.includes('@deprecated') || docString.includes('deprecated')) return true;

    return false;
}

/**
 * Check if a function is async.
 */
function isAsync(fn: any): boolean {
    return fn?.constructor?.name === 'AsyncFunction';
}

/**
 * Extract function signature.
 */
function getSignature(fn: any, name: string): string {
    if (!fn) return '';

    try {
        const fnStr = fn.toString();
        const match = fnStr.match(/^(async\s+)?function\s*\w*\s*\((.*?)\)/);
        if (match) {
            return `(${match[2]})`;
        }

        const arrowMatch = fnStr.match(/^(async\s*)?\((.*?)\)\s*=>/);
        if (arrowMatch) {
            return `(${arrowMatch[2]})`;
        }

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
function hasDocstring(obj: any): boolean {
    if (!obj) return false;

    const objStr = obj.toString();
    return objStr.includes('/**') || objStr.includes('//');
}

/**
 * Introspect a module/object recursively.
 */
function introspectModule(
    obj: any,
    moduleName: string,
    parentPath: string = '',
    depth: number = 0,
    maxDepth: number = 3,
    exportedNames: Set<string> | null = null
): APIMetadata[] {
    const apis: APIMetadata[] = [];

    if (depth > maxDepth || !obj || typeof obj !== 'object') {
        return apis;
    }

    const seen = new Set<string>();

    const allNames = new Set([
        ...Object.keys(obj),
        ...Object.getOwnPropertyNames(obj)
    ]);

    for (const name of allNames) {
        if (name.startsWith('_')) continue;

        if (['constructor', 'prototype', '__proto__', 'length', 'name', 'arguments', 'caller'].includes(name)) continue;

        try {
            const member = obj[name];
            if (!member) continue;

            const memberId = `${parentPath}.${name}`;
            if (seen.has(memberId)) continue;
            seen.add(memberId);

            const fullName = parentPath ? `${parentPath}.${name}` : name;
            const inExports = exportedNames ? exportedNames.has(name) : true;

            const memberType = typeof member;

            if (memberType === 'function') {
                const isClass = member.toString().startsWith('class ');

                if (isClass) {
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
                                // Skip
                            }
                        }
                    }

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
                            // Skip
                        }
                    }
                } else {
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
            } else if (memberType === 'object' && !Array.isArray(member) && depth < maxDepth) {
                const subApis = introspectModule(member, moduleName, fullName, depth + 1, maxDepth, null);
                apis.push(...subApis);
            }
        } catch (e) {
            continue;
        }
    }

    return apis;
}

/**
 * Main introspection logic.
 */
function main(): void {
    const args = process.argv.slice(2);

    if (args.length < 2) {
        console.error('Usage: ts-node typescript_introspect.ts <library_name> <version> [modules...]');
        process.exit(1);
    }

    const libraryName = args[0];
    const version = args[1];
    const modules = args.length > 2 ? args.slice(2) : [libraryName];

    let allApis: APIMetadata[] = [];

    for (const moduleName of modules) {
        try {
            const module = require(moduleName);
            const exportedNames = new Set(Object.keys(module));
            const apis = introspectModule(module, moduleName, moduleName, 0, 3, exportedNames);
            allApis.push(...apis);
        } catch (e: any) {
            console.error(`ERROR: Failed to import ${moduleName}: ${e.message}`);
            continue;
        }
    }

    const byType: Record<string, number> = {};
    for (const api of allApis) {
        const apiType = api.type;
        byType[apiType] = (byType[apiType] || 0) + 1;
    }

    const output: IntrospectionOutput = {
        library: libraryName,
        version: version,
        language: 'typescript',
        total_apis: allApis.length,
        apis: allApis,
        by_type: byType,
        deprecated_count: allApis.filter(a => a.is_deprecated).length
    };

    console.log(JSON.stringify(output, null, 2));
}

main();
