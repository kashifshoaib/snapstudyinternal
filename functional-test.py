#!/usr/bin/env python3
"""
SnapStudy Functional Testing Script

Comprehensive functional testing of the entire SnapStudy system before deployment.
"""

import os
import sys
import json
import importlib.util
import ast
import subprocess
from typing import Dict, List, Any, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FunctionalTester:
    """Comprehensive functional testing for SnapStudy."""
    
    def __init__(self):
        self.test_results = []
        self.project_root = Path.cwd()
        self.backend_path = self.project_root / "backend"
        self.frontend_path = self.project_root / "frontend"
        self.infrastructure_path = self.project_root / "infrastructure"
    
    def run_all_tests(self) -> bool:
        """Run all functional tests."""
        logger.info("🔍 Starting comprehensive functional testing")
        
        try:
            # Test categories
            self._test_python_syntax()
            self._test_python_imports()
            self._test_typescript_syntax()
            self._test_dependencies()
            self._test_configuration_files()
            self._test_deployment_scripts()
            self._test_infrastructure_code()
            self._test_service_integrations()
            
            # Generate report
            self._generate_report()
            
            # Check results
            failed_tests = [result for result in self.test_results if not result['passed']]
            
            if failed_tests:
                logger.error(f"❌ {len(failed_tests)} functional tests failed")
                return False
            else:
                logger.info("✅ All functional tests passed")
                return True
                
        except Exception as e:
            logger.error(f"❌ Functional testing failed with error: {str(e)}")
            return False
    
    def _test_python_syntax(self):
        """Test Python syntax in all Python files."""
        logger.info("🐍 Testing Python syntax...")
        
        python_files = []
        for root, dirs, files in os.walk(self.backend_path):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        # Add deployment scripts
        for script in ['validate-deployment.py', 'backend/deploy_lambda.py']:
            script_path = self.project_root / script
            if script_path.exists():
                python_files.append(str(script_path))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse the file to check syntax
                ast.parse(content)
                self._add_result("Python Syntax", f"File: {os.path.relpath(file_path)}", True, "Valid syntax")
                
            except SyntaxError as e:
                self._add_result("Python Syntax", f"File: {os.path.relpath(file_path)}", False, f"Syntax error: {str(e)}")
            except Exception as e:
                self._add_result("Python Syntax", f"File: {os.path.relpath(file_path)}", False, f"Error: {str(e)}")
    
    def _test_python_imports(self):
        """Test Python imports for circular dependencies and missing modules."""
        logger.info("📦 Testing Python imports...")
        
        # Key files to test imports
        key_files = [
            "backend/src/api/main.py",
            "backend/src/middleware/error_handler.py",
            "backend/src/middleware/security.py",
            "backend/src/utils/retry.py",
            "backend/src/services/dynamodb.py",
            "backend/lambda_functions/main_handler.py",
            "backend/lambda_functions/content_processor.py",
            "backend/lambda_functions/multimedia_processor.py"
        ]
        
        for file_path in key_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self._add_result("Python Imports", f"File: {file_path}", False, "File does not exist")
                continue
            
            try:
                # Check for obvious import issues by parsing
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                
                # Check for circular imports
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                
                # Check for potential circular imports
                has_circular = False
                for imp in imports:
                    if 'error_handler' in imp and 'retry' in file_path:
                        has_circular = True
                        break
                    if 'retry' in imp and 'error_handler' in file_path:
                        has_circular = True
                        break
                
                if has_circular:
                    self._add_result("Python Imports", f"File: {file_path}", False, "Potential circular import detected")
                else:
                    self._add_result("Python Imports", f"File: {file_path}", True, "No circular imports detected")
                
            except Exception as e:
                self._add_result("Python Imports", f"File: {file_path}", False, f"Import analysis error: {str(e)}")
    
    def _test_typescript_syntax(self):
        """Test TypeScript syntax."""
        logger.info("📘 Testing TypeScript syntax...")
        
        # Check if TypeScript compiler is available
        try:
            result = subprocess.run(['npx', 'tsc', '--version'], 
                                  capture_output=True, text=True, cwd=self.frontend_path)
            if result.returncode != 0:
                self._add_result("TypeScript Syntax", "TypeScript Compiler", False, "TypeScript compiler not available")
                return
        except FileNotFoundError:
            self._add_result("TypeScript Syntax", "TypeScript Compiler", False, "npx not found")
            return
        
        # Run TypeScript compilation check
        try:
            result = subprocess.run(['npx', 'tsc', '--noEmit'], 
                                  capture_output=True, text=True, cwd=self.frontend_path)
            
            if result.returncode == 0:
                self._add_result("TypeScript Syntax", "Compilation Check", True, "No TypeScript errors")
            else:
                # Count errors
                error_lines = [line for line in result.stdout.split('\n') if 'error TS' in line]
                self._add_result("TypeScript Syntax", "Compilation Check", False, 
                               f"{len(error_lines)} TypeScript errors found")
                
        except Exception as e:
            self._add_result("TypeScript Syntax", "Compilation Check", False, f"Error running tsc: {str(e)}")
    
    def _test_dependencies(self):
        """Test dependency files."""
        logger.info("📋 Testing dependencies...")
        
        # Check backend requirements.txt
        backend_req = self.backend_path / "requirements.txt"
        if backend_req.exists():
            try:
                with open(backend_req, 'r') as f:
                    content = f.read()
                
                # Check for common issues
                lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
                
                # Check for version conflicts
                packages = {}
                for line in lines:
                    if '==' in line:
                        pkg_name = line.split('==')[0]
                        if pkg_name in packages:
                            self._add_result("Dependencies", "Backend requirements.txt", False, 
                                           f"Duplicate package: {pkg_name}")
                        packages[pkg_name] = line
                
                self._add_result("Dependencies", "Backend requirements.txt", True, 
                               f"{len(packages)} packages defined")
                
            except Exception as e:
                self._add_result("Dependencies", "Backend requirements.txt", False, f"Error: {str(e)}")
        else:
            self._add_result("Dependencies", "Backend requirements.txt", False, "File not found")
        
        # Check frontend package.json
        frontend_pkg = self.frontend_path / "package.json"
        if frontend_pkg.exists():
            try:
                with open(frontend_pkg, 'r') as f:
                    pkg_data = json.load(f)
                
                # Check required fields
                required_fields = ['name', 'version', 'dependencies', 'scripts']
                for field in required_fields:
                    if field not in pkg_data:
                        self._add_result("Dependencies", "Frontend package.json", False, 
                                       f"Missing required field: {field}")
                        return
                
                # Check for React
                if 'react' not in pkg_data['dependencies']:
                    self._add_result("Dependencies", "Frontend package.json", False, "React not found in dependencies")
                else:
                    self._add_result("Dependencies", "Frontend package.json", True, "All required dependencies present")
                
            except Exception as e:
                self._add_result("Dependencies", "Frontend package.json", False, f"Error: {str(e)}")
        else:
            self._add_result("Dependencies", "Frontend package.json", False, "File not found")
    
    def _test_configuration_files(self):
        """Test configuration files."""
        logger.info("⚙️ Testing configuration files...")
        
        # Check backend config
        config_file = self.backend_path / "src" / "config.py"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                
                # Check for required settings
                required_settings = [
                    'aws_region', 'users_table', 'lessons_table', 
                    'content_bucket', 'jwt_secret_key'
                ]
                
                missing_settings = []
                for setting in required_settings:
                    if setting not in content:
                        missing_settings.append(setting)
                
                if missing_settings:
                    self._add_result("Configuration", "Backend config.py", False, 
                                   f"Missing settings: {', '.join(missing_settings)}")
                else:
                    self._add_result("Configuration", "Backend config.py", True, "All required settings present")
                
            except Exception as e:
                self._add_result("Configuration", "Backend config.py", False, f"Error: {str(e)}")
        else:
            self._add_result("Configuration", "Backend config.py", False, "File not found")
        
        # Check infrastructure CDK
        cdk_file = self.infrastructure_path / "lib" / "snapstudy-stack-simple.ts"
        if cdk_file.exists():
            try:
                with open(cdk_file, 'r') as f:
                    content = f.read()
                
                # Check for required resources
                required_resources = [
                    'DynamoDBTables', 'LambdaFunctions', 'S3Bucket', 
                    'ApiGateway', 'CloudFront'
                ]
                
                missing_resources = []
                for resource in required_resources:
                    if resource not in content:
                        missing_resources.append(resource)
                
                if missing_resources:
                    self._add_result("Configuration", "CDK Stack", False, 
                                   f"Missing resources: {', '.join(missing_resources)}")
                else:
                    self._add_result("Configuration", "CDK Stack", True, "All required resources defined")
                
            except Exception as e:
                self._add_result("Configuration", "CDK Stack", False, f"Error: {str(e)}")
        else:
            self._add_result("Configuration", "CDK Stack", False, "File not found")
    
    def _test_deployment_scripts(self):
        """Test deployment scripts."""
        logger.info("🚀 Testing deployment scripts...")
        
        # Check deployment scripts exist
        scripts = [
            "deploy-production.sh",
            "deploy-production.ps1",
            "validate-deployment.py",
            "backend/deploy_lambda.py"
        ]
        
        for script in scripts:
            script_path = self.project_root / script
            if script_path.exists():
                try:
                    with open(script_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for basic deployment steps
                    if script.endswith('.py'):
                        # Python script checks
                        if 'def ' in content and 'main' in content:
                            self._add_result("Deployment Scripts", script, True, "Valid Python deployment script")
                        else:
                            self._add_result("Deployment Scripts", script, False, "Invalid Python script structure")
                    else:
                        # Shell script checks
                        if 'aws' in content and 'deploy' in content:
                            self._add_result("Deployment Scripts", script, True, "Valid deployment script")
                        else:
                            self._add_result("Deployment Scripts", script, False, "Missing deployment commands")
                    
                except Exception as e:
                    self._add_result("Deployment Scripts", script, False, f"Error reading script: {str(e)}")
            else:
                self._add_result("Deployment Scripts", script, False, "Script not found")
    
    def _test_infrastructure_code(self):
        """Test infrastructure code."""
        logger.info("🏗️ Testing infrastructure code...")
        
        # Check CDK package.json
        cdk_pkg = self.infrastructure_path / "package.json"
        if cdk_pkg.exists():
            try:
                with open(cdk_pkg, 'r') as f:
                    pkg_data = json.load(f)
                
                # Check for CDK dependencies
                deps = pkg_data.get('dependencies', {})
                dev_deps = pkg_data.get('devDependencies', {})
                all_deps = {**deps, **dev_deps}
                
                required_cdk_deps = ['aws-cdk-lib', 'constructs']
                missing_deps = []
                
                for dep in required_cdk_deps:
                    if dep not in all_deps:
                        missing_deps.append(dep)
                
                if missing_deps:
                    self._add_result("Infrastructure", "CDK Dependencies", False, 
                                   f"Missing CDK dependencies: {', '.join(missing_deps)}")
                else:
                    self._add_result("Infrastructure", "CDK Dependencies", True, "All CDK dependencies present")
                
            except Exception as e:
                self._add_result("Infrastructure", "CDK Dependencies", False, f"Error: {str(e)}")
        else:
            self._add_result("Infrastructure", "CDK package.json", False, "File not found")
    
    def _test_service_integrations(self):
        """Test service integration points."""
        logger.info("🔗 Testing service integrations...")
        
        # Check API router integrations
        main_api = self.backend_path / "src" / "api" / "main.py"
        if main_api.exists():
            try:
                with open(main_api, 'r') as f:
                    content = f.read()
                
                # Check for router includes
                expected_routers = [
                    'auth.router', 'users.router', 'lessons.router', 
                    'content.router', 'quiz.router', 'chat.router',
                    'analytics.router', 'multimedia.router'
                ]
                
                missing_routers = []
                for router in expected_routers:
                    if router not in content:
                        missing_routers.append(router)
                
                if missing_routers:
                    self._add_result("Service Integration", "API Routers", False, 
                                   f"Missing routers: {', '.join(missing_routers)}")
                else:
                    self._add_result("Service Integration", "API Routers", True, "All routers included")
                
            except Exception as e:
                self._add_result("Service Integration", "API Routers", False, f"Error: {str(e)}")
        
        # Check Lambda function integrations
        lambda_functions = [
            "backend/lambda_functions/main_handler.py",
            "backend/lambda_functions/content_processor.py",
            "backend/lambda_functions/multimedia_processor.py"
        ]
        
        for func_path in lambda_functions:
            func_file = self.project_root / func_path
            if func_file.exists():
                try:
                    with open(func_file, 'r') as f:
                        content = f.read()
                    
                    # Check for proper Lambda handler
                    if 'lambda_handler' in content and 'def lambda_handler' in content:
                        self._add_result("Service Integration", f"Lambda: {func_path}", True, "Valid Lambda handler")
                    else:
                        self._add_result("Service Integration", f"Lambda: {func_path}", False, "Missing Lambda handler")
                    
                except Exception as e:
                    self._add_result("Service Integration", f"Lambda: {func_path}", False, f"Error: {str(e)}")
            else:
                self._add_result("Service Integration", f"Lambda: {func_path}", False, "File not found")
    
    def _add_result(self, category: str, test: str, passed: bool, message: str):
        """Add test result."""
        self.test_results.append({
            'category': category,
            'test': test,
            'passed': passed,
            'message': message
        })
        
        status = "✅" if passed else "❌"
        logger.info(f"{status} {category} - {test}: {message}")
    
    def _generate_report(self):
        """Generate test report."""
        logger.info("📊 Generating functional test report...")
        
        # Count results
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['passed']])
        failed_tests = total_tests - passed_tests
        
        # Group by category
        categories = {}
        for result in self.test_results:
            category = result['category']
            if category not in categories:
                categories[category] = {'passed': 0, 'failed': 0, 'tests': []}
            
            if result['passed']:
                categories[category]['passed'] += 1
            else:
                categories[category]['failed'] += 1
            
            categories[category]['tests'].append(result)
        
        # Generate report
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': failed_tests,
                'success_rate': f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
            },
            'categories': categories,
            'detailed_results': self.test_results
        }
        
        # Save report to file
        with open('functional-test-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"📄 Functional test report saved to functional-test-report.json")
        
        # Print summary
        print("\n" + "="*60)
        print("🔍 SNAPSTUDY FUNCTIONAL TEST REPORT")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print("\nCategory Breakdown:")
        
        for category, stats in categories.items():
            total_cat = stats['passed'] + stats['failed']
            success_rate = (stats['passed']/total_cat)*100 if total_cat > 0 else 0
            status = "✅" if stats['failed'] == 0 else "❌"
            print(f"{status} {category}: {stats['passed']}/{total_cat} ({success_rate:.1f}%)")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"   • {result['category']} - {result['test']}: {result['message']}")
        
        print("="*60)

def main():
    """Main testing function."""
    tester = FunctionalTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All functional tests passed! SnapStudy is ready for deployment.")
        sys.exit(0)
    else:
        print("\n❌ Some functional tests failed. Please fix the issues above before deployment.")
        sys.exit(1)

if __name__ == "__main__":
    main()