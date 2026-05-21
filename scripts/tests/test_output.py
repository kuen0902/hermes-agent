import json
import sys

def main():
    # Read arguments
    args = sys.argv[1:]
    
    # Do some dummy processing
    result = {
        "status": "success",
        "message": "Python script executed successfully",
        "data": {
            "received_args": args,
            "calculated_value": 42
        }
    }
    
    # Print JSON output
    print(json.dumps(result))

if __name__ == "__main__":
    main()
