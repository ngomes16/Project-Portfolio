import os
import importlib.util
import sys

def import_script(script_path):
    """Dynamically import a Python script."""
    spec = importlib.util.spec_from_file_location("module.name", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = module
    spec.loader.exec_module(module)
    return module

def run_all_diagrams():
    # Create images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)
    
    print("Generating methodology and architecture diagrams...")
    
    # List of diagram scripts to run
    diagram_scripts = [
        'create_architecture_diagram.py',
        'create_two_stage_diagram.py',
        'create_augmentation_diagram.py',
        'create_triplet_loss_diagram.py',
        'create_scale_token_diagram.py'
    ]
    
    # Run each script
    for script_name in diagram_scripts:
        print(f"Running {script_name}...")
        try:
            # Option 1: Import and run the main function
            module = import_script(script_name)
            # Assuming each script has a function with the same name as the file
            function_name = script_name.replace('create_', '').replace('.py', '')
            if hasattr(module, function_name):
                getattr(module, function_name)()
            
            # Option 2: Run as subprocess
            # This would be an alternative if import doesn't work well
            # import subprocess
            # subprocess.run([sys.executable, script_name], check=True)
            
            print(f"Successfully ran {script_name}")
        except Exception as e:
            print(f"Error running {script_name}: {e}")
    
    print("\nAll methodology and architecture diagrams generated!")
    print("The following files were created in the 'images' directory:")
    for script_name in diagram_scripts:
        output_name = script_name.replace('create_', '').replace('.py', '') + '.png'
        print(f"  - {output_name}")

if __name__ == "__main__":
    run_all_diagrams() 