if __name__ == "__main__":
    import os
    import gvoiceParser
    import sys
     
    
    path = sys.argv[1]
    for fl in os.listdir(path):
        if (fl.endswith(".html")):
            print gvoiceParser.Parser.process_file(os.path.join(path, fl)).dump()
        
            
        
        
