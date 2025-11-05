{ pkgs, ... }: {
  # Which nixpkgs channel to use.
  channel = "stable-24.05"; 

  # Use the stable python environment and load all dependencies using `withPackages`.
  # This is a more robust way to handle large groups of Python dependencies in Nix.
  packages = [
    # Core System Dependencies
    pkgs.tesseract5
    
    # All Python Packages (consolidated)
    (pkgs.python311.withPackages (python-pkgs: with python-pkgs; [
      # Core Environment
      pip
      
      # Evidence Processing & Data Analysis
      streamlit
      pytesseract
      Pillow
      pandas
      opencv-python
      numpy
      python-dateutil
      tqdm
      openpyxl
      PyPDF2
      python-docx
      moviepy
      SpeechRecognition
      psutil
      reportlab
      matplotlib
      seaborn
      
      # Advanced AI and Legal Analysis
      google-genai
      scikit-learn
      
      # Note: 'firebase-admin' is removed here to resolve the original build error.
      # It can be added back after confirming the correct Nix package name.
    ]))
  ];

  # Sets environment variables in the workspace
  env = {
    # Permanently sets the API key for the Pro Se Veritas AI features
    GEMINI_API_KEY = "AIzaSyCMbuJT7r6HE1vX0tWANYIX71QFj5_adTI";
  };

  idx = {
    # Search for the extensions you want on https://open-vsx.org/
    extensions = [
      "ms-python.python"
      "ms-toolsai.jupyter"
    ];
    
    # Enable previews
    # This 'previews' block is a direct child of the 'idx' block.
    previews = { 
      enable = true;
      previews = {
        web = {
          command = [
            "python3"
            "-m"
            "streamlit"
            "run"
            "streamlit_app.py"
            "--server.port"
            "$PORT"
            "--server.address"
            "0.0.0.0"
            "--server.enableCORS"
            "false"
          ];
          manager = "web";
        };
      };
    };
  };
}
