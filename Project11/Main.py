import CompilationEngineVM
import JackTokenizer
import SymbolTable
import re
import sys
from pathlib import Path


class VMWriter:
    def __init__(self, output_file): self.out = open(output_file, 'w')
    def writePush(self, segment, index): self.out.write(f"push {segment} {index}\n")
    def writePop(self, segment, index): self.out.write(f"pop {segment} {index}\n")
    def writeArithmetic(self, command): self.out.write(f"{command}\n")
    def writeLabel(self, label): self.out.write(f"label {label}\n")
    def writeGoto(self, label): self.out.write(f"goto {label}\n")
    def writeIf(self, label): self.out.write(f"if-goto {label}\n")
    def writeCall(self, name, nArgs): self.out.write(f"call {name} {nArgs}\n")
    def writeFunction(self, name, nLocals): self.out.write(f"function {name} {nLocals}\n")
    def writeReturn(self): self.out.write("return\n")
    def close(self): self.out.close()
def compile_file(jack_path: Path):
    # 1) Read source and tokenize
    jack_source = jack_path.read_text()
    tokenizer = JackTokenizer.JackTokenizer(jack_source)

    # 2) Open VM output
    vm_writer = VMWriter(str(jack_path.with_suffix('.vm')))

    # 3) Symbol table
    sym_table = SymbolTable.SymbolTable()

    # 4) Compile to VM
    engine = CompilationEngineVM.CompilationEngineVM(tokenizer, vm_writer, sym_table)
    engine.compileClass()

    # 5) Flush & close
    vm_writer.close()
    print(f"Compiled {jack_path.name} → {jack_path.with_suffix('.vm').name}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python Main.py <source.jack> | <directory>")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if input_path.is_dir():
        jack_files = sorted(input_path.glob("*.jack"))
        if not jack_files:
            print(f"No .jack files in {input_path}")
            sys.exit(1)
        for jf in jack_files:
            compile_file(jf)

    elif input_path.is_file() and input_path.suffix.lower() == ".jack":
        compile_file(input_path)

    else:
        print("Error: must specify a .jack file or a directory containing .jack files")
        sys.exit(1)

if __name__ == "__main__":
    main()