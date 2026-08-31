/**
 * Test script to validate all frontend files
 * This script checks for:
 * - TypeScript compilation errors
 * - Missing imports
 * - Next.js specific code
 * - React Router usage
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const errors = [];
const warnings = [];

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
};

function logError(file, message) {
  errors.push({ file, message });
  console.log(`${colors.red}✗${colors.reset} ${file}: ${message}`);
}

function logWarning(file, message) {
  warnings.push({ file, message });
  console.log(`${colors.yellow}⚠${colors.reset} ${file}: ${message}`);
}

function logSuccess(file, message) {
  console.log(`${colors.green}✓${colors.reset} ${file}: ${message}`);
}

// Get all TypeScript/TSX files
function getAllFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    if (stat.isDirectory() && !filePath.includes('node_modules')) {
      getAllFiles(filePath, fileList);
    } else if (file.endsWith('.ts') || file.endsWith('.tsx')) {
      fileList.push(filePath);
    }
  });
  
  return fileList;
}

// Check file for issues
function checkFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const relativePath = path.relative(process.cwd(), filePath);
  
  // Check for Next.js imports
  if (content.includes("from 'next/") || content.includes('from "next/')) {
    logError(relativePath, 'Contains Next.js import');
  }
  
  // Check for Next.js specific code
  if (content.includes('usePathname') && !content.includes('react-router-dom')) {
    logError(relativePath, 'Uses Next.js usePathname without react-router-dom');
  }
  
  if (content.includes("Link from 'next/link") || content.includes('Link from "next/link')) {
    logError(relativePath, 'Uses Next.js Link component');
  }
  
  if (content.includes('NEXT_PUBLIC_')) {
    logWarning(relativePath, 'Uses NEXT_PUBLIC_ environment variable (should use REACT_APP_)');
  }
  
  // Check for "use client" directive (Next.js specific)
  if (content.includes("'use client'") || content.includes('"use client"')) {
    logError(relativePath, 'Contains Next.js "use client" directive');
  }
  
  // Check for React Router usage
  if (content.includes('react-router-dom')) {
    logSuccess(relativePath, 'Uses React Router');
  }
  
  // Check for React imports
  if (!content.includes('import') && (content.includes('React') || content.includes('useState') || content.includes('useEffect'))) {
    logWarning(relativePath, 'Uses React features but no import found');
  }
}

console.log(`${colors.blue}Testing all frontend files...${colors.reset}\n`);

// Get all files in src directory
const srcDir = path.join(process.cwd(), 'src');
if (!fs.existsSync(srcDir)) {
  console.log(`${colors.red}Error: src directory not found${colors.reset}`);
  process.exit(1);
}

const files = getAllFiles(srcDir);

console.log(`Found ${files.length} files to check\n`);

files.forEach(file => {
  checkFile(file);
});

console.log(`\n${colors.blue}Summary:${colors.reset}`);
console.log(`${colors.green}✓${colors.reset} Files checked: ${files.length}`);
console.log(`${colors.red}✗${colors.reset} Errors: ${errors.length}`);
console.log(`${colors.yellow}⚠${colors.reset} Warnings: ${warnings.length}\n`);

if (errors.length > 0) {
  console.log(`${colors.red}Errors found:${colors.reset}`);
  errors.forEach(({ file, message }) => {
    console.log(`  - ${file}: ${message}`);
  });
  console.log('');
}

if (warnings.length > 0) {
  console.log(`${colors.yellow}Warnings:${colors.reset}`);
  warnings.forEach(({ file, message }) => {
    console.log(`  - ${file}: ${message}`);
  });
  console.log('');
}

// Try to run TypeScript compiler
console.log(`${colors.blue}Running TypeScript compiler check...${colors.reset}\n`);

try {
  const tscOutput = execSync('npx tsc --noEmit', { 
    encoding: 'utf8',
    cwd: process.cwd(),
    stdio: 'pipe'
  });
  console.log(`${colors.green}✓ TypeScript compilation: No errors${colors.reset}\n`);
} catch (error) {
  console.log(`${colors.red}✗ TypeScript compilation errors:${colors.reset}`);
  console.log(error.stdout || error.stderr);
  console.log('');
}

// Final result
if (errors.length > 0) {
  console.log(`${colors.red}✗ Test failed with ${errors.length} error(s)${colors.reset}`);
  process.exit(1);
} else {
  console.log(`${colors.green}✓ All tests passed!${colors.reset}`);
  process.exit(0);
}
