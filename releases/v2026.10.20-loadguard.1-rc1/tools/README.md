# Native load guard builder

Developer-only: Python 3.10+ and Capstone are required. Player installers need only the bundled standard-library Python.

Pass a legally obtained, decrypted BLJM60012 original ELF and the existing delta.5 Chinese AcParts.bin. The builder requires exact baseline SHA-256 values, validates all 202 slots, extends only the documented zero-filled load-segment gap, declares the new executable/data sections, and writes a new ELF plus disassembly/report. It does not decrypt the original SELF and supplies no console keys.

```
python build_load_guard.py --elf EBOOT.original.elf --parts AcParts.chinese.bin --out candidate
```

Packaging used the official PSL1GHT `tools/fself` source. Its `self_build_sceversion_header` was adapted to return an empty version record when `.sceversion` section names are absent (`sce_idx < 0 || sce_off == (uint64_t)-1`), avoiding an invalid pointer. The resulting debug SELF embeds the generated ELF byte-for-byte. No signature claim or physical-console compatibility claim is made.

The diagnostic build temporarily emitted TTY messages after the 202-entry loop and a check of the reported head-part string. Those diagnostic instructions are excluded from the distributable. Runtime evidence confirms the real parser path was reached twice from Japanese input; interactive old-save selection remains pending.
