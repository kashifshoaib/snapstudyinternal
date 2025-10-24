const { execSync } = require('child_process');

try {
  console.log('Running frontend component tests...');
  
  // Try to run tests using the existing test script
  execSync('npm test -- --watchAll=false --verbose', { 
    stdio: 'inherit',
    cwd: __dirname 
  });
  
  console.log('All tests completed successfully!');
} catch (error) {
  console.error('Test execution failed:', error.message);
  process.exit(1);
}