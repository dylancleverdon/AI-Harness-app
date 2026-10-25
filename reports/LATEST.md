# Diagnostics — fastpass 3 — 2026-10-24 19:28:19


## Run

```
script: decomp_pipeline 2026-10-25.8 (build 2026-10-18.1)
command: /Users/admin/AIHarness/scripts/decomp_pipeline.py --workdir /Users/admin/glitchdecomp/fastpass 3 --from export --to organize --headless-export --ghidra-home /Users/admin/Downloads/ghidra_12.1.4_PUBLIC --project /Users/admin/glitchpt2.gpr --ctx 8192 --parallel 50 --workers 12 --lang c --no-pseudo --repair-minutes 1 --plugin /Users/admin/Downloads/Glitch_2_1_5_Mac_Free/Glitch2.component
python: 3.15.0 on darwin
compiler: /usr/bin/clang++ (clang)
compile flags: -Wno-c++11-narrowing -arch arm64
--ctx 8192, chars per token 2.06
model: qwen2.5-coder-3b-instruct-mlx
model requests turned down this run: 0, thinking-only answers: 0
fix stage model edits: {'calls': 2, 'no_answer': 1, 'rejected': 0}
```

## What the script struggled with

```

━━━━ what the script struggled with this run ━━━━
(errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
rates (this run last; earlier runs above it):
  run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
  10-24 17:30               100.0                0.0                  0                  -                  -                  -                  -                 96                  -                  -                     -                0.0
  10-24 17:54               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
  10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
  10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
couldn't handle:
  organize    275 × possible identifying items left (final/ not written)
                    → see the privacy report; add names to privacy_blocklist.txt
  test          1 × the rebuilt plugin didn't load: load executable   [also in the last 2 run(s)]
                    → see build/test/test_report.txt
worked around (cost time, nothing lost):
  fix         120 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
  fix           1 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_0029db84
  fix           1 × small edits the model couldn't give a usable answer for
  link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Log of this run (pipeline.log)

```
[19:15:38] decomp_pipeline 2026-10-25.8: /Users/admin/glitchdecomp/fastpass 3 — stages export → organize
[19:15:38]   --ctx 8192: pieces up to 5303 characters, recover stage up to 11006
[19:15:38] ━━━━ Stage 1/10 · export ━━━━ getting every function's pseudocode from Ghidra (once — after that Ghidra can be closed)
[19:15:38]   snapshot of the current files before 'redo-data-export': /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-191538-redo-data-export
[19:15:38]   exporting the program's data with Ghidra headless (no decompiling)
[19:15:44]   using the existing ghidra_export.json (Ghidra not needed)
[19:15:45]   Ghidra lost the return value of 6 function(s) (0 of them empty: they return what they're given): fixing their signatures and decompiling them and their callers again (headless, read-only)
[19:15:53]   signature fix: 6 function(s) given back their return value, 436 decompiled again with it
[19:16:00]   callgraph.json: 22076 functions with internal calls
[19:16:00]   export: 30489/30489 functions have pseudocode, 205 data types, 30489 signatures
[19:16:00] ━━━━ Stage 2/10 · privacy ━━━━ identifying information (names, web and email addresses, bundle IDs, paths, copyright lines) is replaced in Ghidra's export, before anything else sees it; what was replaced is kept in private/ on this Mac only
[19:16:03]   privacy: 1141 replacement(s) in Ghidra's export (6 names, 14 web addresses, 8 copyright lines, 1 email address, 3 user folders, 3 bundle IDs). What was replaced: private/privacy_report.txt (stays on this Mac)
[19:16:03]   privacy: 17 stand-in(s) are values the plugin uses while it runs (bundle ID, web addresses): the rebuilt plugin's Info.plist must use the same ones (listed in private/privacy_report.txt)
[19:16:03] ━━━━ Stage 3/10 · rewrite ━━━━ Ghidra's pseudocode is written out as one C file, with the program's data (no model: the code is what Ghidra decompiled)
[19:16:32]     functions with a system function's name (the system's is used): 3: sync, setbuf, objc_msgSend
[19:16:32]     Ghidra's copies of types the system headers define (the system's are used): 63, e.g. Byte, CGPoint, CGRect, CGSize, FILE, SEL
[19:16:32]     fields Ghidra named that the system's type calls something else (read at their offset): 14
[19:16:36]     pointers only the loader's fix-up list has (no reference in Ghidra): 583, fixed up too
[19:16:36]     static initializers the plugin runs when it loads (as the original does): 91
[19:16:36]     pointers in the data to addresses outside it (not fixed up): 7, listed in rewrite/data_unresolved_pointers.txt
[19:16:36]     data found by its address (not in Ghidra's label list): 496
[19:17:26]     addresses in the data written in the code as numbers ((long *)0x453400): 320, now the rebuilt data's
[19:17:41]     pieces of variables (v._0_8_): 6357
[19:17:41]     functions Ghidra said return nothing, whose callers use the result: 2949
[19:17:41]     16-byte register values (as gh16): 1908
[19:17:41]     C++/Objective-C names in definitions: 1285
[19:17:41]     C++ qualified names in code: 190
[19:17:41]     types C didn't know (declared opaque): 19
[19:17:41]     types that are also functions (as struct tags): 18
[19:17:41]     switches on a pointer (on its value): 11
[19:17:41]     NAN(x) tests (as isnan): 8
[19:17:41]     of those, returning a stand-in 0 (nothing to return in Ghidra's code): 2225, listed in rewrite/lost_returns.txt
[19:17:46]     names that are a type and also a function (the type keeps its struct tag): 12
[19:17:46]   C source from Ghidra's pseudocode: 30173 function(s), 311 library stub(s) called directly, 29 data type(s) with Ghidra's layout, the program's data (35 block(s), 2997 labelled location(s) used, 33768 pointer fix-up(s), 1 placeholder(s) for data outside the export: rewrite/data_placeholders.txt) -> pseudocode.c
[19:17:46] ━━━━ Stage 4/10 · split ━━━━ libclang splits the rewrite into shared.h + one file per function, repairs the header, then compiles every function on its own
[19:22:20] ━━━━ Stage 5/10 · fix ━━━━ functions that don't compile are repaired, callees first: quick deterministic fixes, then the model; what can't be fixed is quarantined
[19:25:45]   fix: 5 model request(s); the model was busy 3% of the stage's 3m
[19:25:45] ━━━━ Stage 6/10 · recover ━━━━ quarantined functions are rebuilt from their Ghidra pseudocode
[19:25:45] ━━━━ Stage 7/10 · link ━━━━ the whole program is compiled and linked; anything still missing gets a placeholder and is listed in link_report.txt
[19:27:58] ━━━━ Stage 8/10 · test ━━━━ the rebuilt plugin and the original (--plugin) render the same test signals in a small test host; their outputs are compared sample by sample
[19:28:04]   test: the rebuilt plugin didn't load: crashed (SIGSEGV) during: load executable
[19:28:04]   test: everything it saw is in /Users/admin/glitchdecomp/fastpass 3/build_c/test/test_report.txt
[19:28:04] ━━━━ Stage 9/10 · improve ━━━━ the code is made easier to read (names, Ghidra's helpers, casts, pointer arithmetic), worst functions first; a change is kept only if the function compiles to the same machine code, so the plugin does exactly what it did
[19:28:04]   improve: off (it's slow, and optional: the final code builds without it). Turn it on with --improve
[19:28:04] ━━━━ Stage 10/10 · organize ━━━━ the whole program is written out as one C source file, final/program.c, with its headers, its data and build.sh; final/ is only replaced once that builds
[19:28:19] ============================================================
[19:28:19] SUMMARY: 30173/30173 functions compile, 0 quarantined, 2 re-derived, link=OK
[19:28:19] Report: /Users/admin/glitchdecomp/fastpass 3/REPORT.md
[19:28:19] 
[19:28:19] ━━━━ what the script struggled with this run ━━━━
[19:28:19] (errors it fixed on its own are left out; [also in the last N runs] marks the ones worth changing the script for)
[19:28:19] rates (this run last; earlier runs above it):
[19:28:19]   run                   compile %      quarantined %             to fix        fixer tried    fixer success %     fixer per hour  recover success %      learned fixes     learned kept %            rescued  ideas adopted/tested        test pass %
[19:28:19]   10-24 17:30               100.0                0.0                  0                  -                  -                  -                  -                 96                  -                  -                     -                0.0
[19:28:19]   10-24 17:54               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[19:28:19]   10-24 18:26               100.0                0.0                  0                  -                  -                  -                  -                 96               98.1                  -                     -                0.0
[19:28:19]   10-24 18:56               100.0                0.0                  0                  -                  -                  -                  -                  -                  -                  -                     -                0.0
[19:28:19]   10-24 19:28               100.0                0.0                  0                  1              100.0                 23                  -                 97               98.6                  -                     -                0.0
[19:28:19] couldn't handle:
[19:28:19]   organize    275 × possible identifying items left (final/ not written)
[19:28:19]                     → see the privacy report; add names to privacy_blocklist.txt
[19:28:19]   test          1 × the rebuilt plugin didn't load: load executable   [also in the last 2 run(s)]
[19:28:19]                     → see build/test/test_report.txt
[19:28:19] worked around (cost time, nothing lost):
[19:28:19]   fix         120 × Ghidra globals / library functions nothing declared (declared once in shared.h)   e.g. LAB_001806a4   [also in the last 5 run(s)]
[19:28:19]   fix           1 × fixes that undid each other (the cycle was stopped and the model got the function)   e.g. FUN_0029db84
[19:28:19]   fix           1 × small edits the model couldn't give a usable answer for
[19:28:19]   link         24 × functions replaced by placeholders to link   [also in the last 5 run(s)]
```

## Build status

```
{
 "functions": 30173,
 "compile": 30173,
 "quarantined": 0,
 "to fix": 0
}
```

## build/split_report.txt

```
unresolved struct fields (unknown type, left as comments): 0
```

## build/libclang_parse_errors.txt

```
_parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
_parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
```

## build/header_repair_report.txt

```
disabled proto out_of_range   <- redefinition of 'out_of_range' as different kind of symbol
disabled proto length_error   <- redefinition of 'length_error' as different kind of symbol
```

## build/fix_report.txt

```
why 0 function(s) are quarantined (first compile error, grouped):
```

## build/link_report.txt

```
stubbed DAT_0042e5a8 (never defined)
stubbed FUN_00230160 (never defined)
stubbed FUN_00315c (never defined)
stubbed FUN_004536f8 (never defined)
stubbed FUN_00453790 (never defined)
stubbed FUN_004537b8 (never defined)
stubbed FUN_00453810 (never defined)
stubbed FUN_004538a8 (never defined)
stubbed FUN_004538c0 (never defined)
stubbed FUN_00453900 (never defined)
stubbed FUN_00453d30 (never defined)
stubbed FUN_00453d70 (never defined)
stubbed FUN_00453e28 (never defined)
stubbed FUN_00454130 (never defined)
stubbed FUN_00454148 (never defined)
stubbed FUN_00454268 (never defined)
stubbed FUN_008716a0 (never defined)
stubbed _init (not in the program or the system libraries: a placeholder)
_logf: forwarded to the library's logf
_next_prime: forwarded to the library's _ZNSt3__112__next_primeEm
stubbed _throw_length_error (not in the program or the system libraries: a placeholder)
addButtonWithTitle_: an Objective-C message (addButtonWithTitle:), sent for real
addObserver_selector_name_object_: an Objective-C message (addObserver:selector:name:object:), sent for real
applicationShouldTerminate_: an Objective-C message (applicationShouldTerminate:), sent for real
arrayWithCapacity_: an Objective-C message (arrayWithCapacity:), sent for real
arrayWithObject_: an Objective-C message (arrayWithObject:), sent for real
arrayWithObjects_: an Objective-C message (arrayWithObjects:), sent for real
arrayWithObjects_count_: an Objective-C message (arrayWithObjects:count:), sent for real
buildMenuGroupEntries_entry_: an Objective-C message (buildMenuGroupEntries:entry:), sent for real
bundleWithPath_: an Objective-C message (bundleWithPath:), sent for real
characterAtIndex_: an Objective-C message (characterAtIndex:), sent for real
constraintWithItem_attribute_relatedBy_toItem_attribute_multiplier_constant_: an Objective-C message (constraintWithItem:attribute:relatedBy:toItem:attribute:multiplier:constant:), sent for real
convertRectFromBacking_: an Objective-C message (convertRectFromBacking:), sent for real
convertRectToBacking_: an Objective-C message (convertRectToBacking:), sent for real
createLayerTextureWithSize_: an Objective-C message (createLayerTextureWithSize:), sent for real
defaultWritingDirectionForLanguage_: an Objective-C message (defaultWritingDirectionForLanguage:), sent for real
deminiaturize_: an Objective-C message (deminiaturize:), sent for real
dictionaryWithContentsOfFile_: an Objective-C message (dictionaryWithContentsOfFile:), sent for real
drawRect_: an Objective-C message (drawRect:), sent for real
fileURLWithPath_: an Objective-C message (fileURLWithPath:), sent for real
getReturnValue_: an Objective-C message (getReturnValue:), sent for real
graphicsContextWithWindow_: an Objective-C message (graphicsContextWithWindow:), sent for real
initWithContentRect_styleMask_backing_defer_: an Objective-C message (initWithContentRect:styleMask:backing:defer:), sent for real
initWithContentsOfFile_: an Objective-C message (initWithContentsOfFile:), sent for real
initWithFrame_: an Objective-C message (initWithFrame:), sent for real
initWithFrame_frame_: an Objective-C message (initWithFrame:frame:), sent for real
initWithImage_hotSpot_: an Objective-C message (initWithImage:hotSpot:), sent for real
initWithString_: an Objective-C message (initWithString:), sent for real
initWithTitle_: an Objective-C message (initWithTitle:), sent for real
initWithTitle_action_keyEquivalent_: an Objective-C message (initWithTitle:action:keyEquivalent:), sent for real
insertText_: an Objective-C message (insertText:), sent for real
invocationWithMethodSignature_: an Objective-C message (invocationWithMethodSignature:), sent for real
invokeWithTarget_: an Objective-C message (invokeWithTarget:), sent for real
keyEquivalentFromMenuEntry_: an Objective-C message (keyEquivalentFromMenuEntry:), sent for real
markedTextAbandoned_: an Objective-C message (markedTextAbandoned:), sent for real
miniaturize_: an Objective-C message (miniaturize:), sent for real
modflagsFromMenuEntry_: an Objective-C message (modflagsFromMenuEntry:), sent for real
objectAtIndex_: an Objective-C message (objectAtIndex:), sent for real
objectForKey_: an Objective-C message (objectForKey:), sent for real
operator_delete: forwarded to the library's _ZdlPv
operator_delete__: forwarded to the library's _ZdaPv
operator_new__: forwarded to the library's _Znam
otherEventWithType_location_modifierFlags_timestamp_windowNumber_context_subtype_data1_data2_: an Objective-C message (otherEventWithType:location:modifierFlags:timestamp:windowNumber:context:subtype:data1:data2:), sent for real
performClose_: an Objective-C message (performClose:), sent for real
performFileOperation_source_destination_files_tag_: an Objective-C message (performFileOperation:source:destination:files:tag:), sent for real
removeObserver_: an Objective-C message (removeObserver:), sent for real
respondsToSelector_: an Objective-C message (respondsToSelector:), sent for real
scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_: an Objective-C message (scheduledTimerWithTimeInterval:target:selector:userInfo:repeats:), sent for real
sendEvent_: an Objective-C message (sendEvent:), sent for real
setAllowGPUOptimizedContents_: an Objective-C message (setAllowGPUOptimizedContents:), sent for real
setAllowGettingClosed_: an Objective-C message (setAllowGettingClosed:), sent for real
setAutoForwardKeyEvents_: an Objective-C message (setAutoForwardKeyEvents:), sent for real
setCanChooseFiles_: an Objective-C message (setCanChooseFiles:), sent for real
setCanCreateDirectories_: an Objective-C message (setCanCreateDirectories:), sent for real
setCommandQueue_: an Objective-C message (setCommandQueue:), sent for real
setContentSizeConstraints_: an Objective-C message (setContentSizeConstraints:), sent for real
setContentSize_: an Objective-C message (setContentSize:), sent for real
setCppParent_: an Objective-C message (setCppParent:), sent for real
setCppWindow_: an Objective-C message (setCppWindow:), sent for real
setCpuCacheMode_: an Objective-C message (setCpuCacheMode:), sent for real
setCurrentInterpretKeyEventsKey_: an Objective-C message (setCurrentInterpretKeyEventsKey:), sent for real
setFrame_display_: an Objective-C message (setFrame:display:), sent for real
setMenuBarVisible_: an Objective-C message (setMenuBarVisible:), sent for real
setPluginShell_: an Objective-C message (setPluginShell:), sent for real
setSelector_: an Objective-C message (setSelector:), sent for real
setStyleMask_: an Objective-C message (setStyleMask:), sent for real
setSubmenu_: an Objective-C message (setSubmenu:), sent for real
setTexture_: an Objective-C message (setTexture:), sent for real
setTitle_: an Objective-C message (setTitle:), sent for real
setUsage_: an Objective-C message (setUsage:), sent for real
stringWithCharacters_length_: an Objective-C message (stringWithCharacters:length:), sent for real
stringWithFormat_: an Objective-C message (stringWithFormat:), sent for real
stringWithUTF8String_: an Objective-C message (stringWithUTF8String:), sent for real
texture2DDescriptorWithPixelFormat_width_height_mipmapped_: an Objective-C message (texture2DDescriptorWithPixelFormat:width:height:mipmapped:), sent for real
updateLayerInRect_: an Objective-C message (updateLayerInRect:), sent for real
validateMenuItem_: an Objective-C message (validateMenuItem:), sent for real
viewWillMoveToSuperview_: an Objective-C message (viewWillMoveToSuperview:), sent for real
zoom_: an Objective-C message (zoom:), sent for real
```

## build/link_errors.txt

```
ld: warning: ignoring duplicate libraries: '-lc++'
Undefined symbols for architecture arm64:
  "_length_error", referenced from:
      _gd_targets in ghidra_data.o
  "_out_of_range", referenced from:
      _gd_targets in ghidra_data.o
ld: symbol(s) not found for architecture arm64
clang++: error: linker command failed with exit code 1 (use -v to see invocation)
```

## build/learned_fixes.txt

```
Fixes this project learned from the model's edits (@1, @2 ... stand for any
name). Proven ones are applied without the model; candidates are tried on
every function with the same error and kept only where they work.

== proven: 97
[338 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @1 = @3(@4);
[206 worked, 53 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → unsigned char @1[16] = {0};@2(
[203 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];
  → uint64_t @2;
[202 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1 = @2((@3)@4);
  → @1 = @2((@3)@4, 1);
[175 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 1;
  → *(unsigned char*)&@1 = (unsigned char)1;
[170 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, 1);
  → @1 = @2(*(unsigned char*)&@1, 1);
[112 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → unsigned char @1[16] = {0};@2(@3);
[92 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    (@1);
  → (@1, 1);
[87 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → *(unsigned char*)&@1 = @2(@3, @4);
[82 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16];
[73 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2.@3;
  → @1 = @2[8];
[70 worked, 12 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2;
[69 worked, 6 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case 0 :
[64 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (void*)@2(
  → @1 = @2(
[60 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    )@1);
  → )@1, 1);
[44 worked, 12 didn't] initializing 'X' with an expression of incompatible type 'X' (part of a line)
    @1 = @2(
  → @1 = (unsigned long long)@2(
[43 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2.@3;
  → *(unsigned char*)&@1 = *(unsigned char*)&@2;
[35 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2();
  → (void)@1 = @2();
[31 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2);
  → @1(@2, 1);
[30 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3;
  → @1[8] = @3;
[29 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 0;
  → @1[8] = 0;
[27 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1, (
  → 0], (
[25 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → unsigned char @1[16];@2(@3, @4);
[25 worked, 6 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2();
  → uint64_t @1 = @2();
[21 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16] = {0};@2(@3, @4, @5);
[19 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((long)@3);
  → uintptr_t @1 = @2((long)@3);
[18 worked, 1 didn't] too few arguments to function call, expected N, have N (part of a line)
    @1();
  → @1(1);
[18 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2((
  → @1 = ((uint64_t(*)())@2)((
[18 worked, 8 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[1] = {0};@2(
[16 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long)@2(@3, @4);
  → long @1 = @2(@3, @4);
[14 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, @4);
  → @1 = @2(*(unsigned int*)&@1, @4);
[14 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16] = {0};@2();
[13 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1(@2
  → ((uint64_t(*)())@1)(@2
[12 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
[12 worked, 2 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[16] = {0};(*
[11 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0;
  → @1[0] = 0;
[11 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case 1 :
[10 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    int @1 = (int)@2(
  → long @1 = @2(
[9 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2, @1.@3, @4.@2, @4.@3, @5.@2,
  → , @1[0], @1[8], @4[0], @4[8], @5[0], @5[8]);
[8 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4, @3.@5, @6, @7);
  → @1 = @2(@3, @6, @7);
[8 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(@2[0]);
  → @1(@2[0], 1);
[8 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    long)@1[0x68]+3
  → long)(@1+0x68)+3
[8 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified (part of a line)
    @1()
  → ((uint64_t(*)())@1)()
[8 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    *(@1(*)[16])(@2+(long)@3) = @4[0];
  → memcpy(&(*(@1(*)[16])(@2+(long)@3)), &(@4[0]), sizeof(*(@1(*)[16])(@2+(long)@3))<sizeof(@4[0]) ? sizeof(*(@1(*)[16])(@2+(long)@3)) : sizeof(@4[0]));
[7 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @1(@1*this)
  → void @1(@1*this)
[7 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@1[0].@3, 1);
  → @1[0] = @2(@1[0], 1);
[7 worked, 0 didn't] redefinition of 'X' (part of a line)
    @1 @2 = {@3
  → @2 = (@1){@3
[6 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2(@3);
  → return std:: @1:: @2(@3);
[6 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((@3*)(@4+0x168));
  → void*@1 = @2((@3*)(@4+0x168));
[6 worked, 0 didn't] variable has incomplete type 'X' (part of a line)
    void std:: @1:: @2(
  → void @2(
[6 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = 0x640001;
  → @1[0] = 0x640001;
[6 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer (part of a line)
    ((@1)(
  → ((int)(
[6 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    )@1[0x68]+2)
  → )@1+0x68*2)
[6 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (long)@2[7]+0x20;
  → @1 = (long)(@2+7)+0x20;
[6 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\b" :
  → case'\b' :
[6 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *@1 =
  → *(uint64_t*)@1 =
[5 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@1.@3, (int)@1+1);
  → @1 = @2(*(unsigned int*)&@1, (int)@1+1);
[5 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@1[0]+1;
  → @1[0] = (int)@1[0]+1;
[5 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2((@3*)(@4+0x88));
  → void*@1 = @2((@3*)(@4+0x88));
[5 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0xd0);
  → long @1 = @3(0xd0);
[5 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    = @1.@2;
  → = @1[0];
[5 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    (1);
  → (1, 0);
[5 worked, 0 didn't] used type 'X' where arithmetic or pointer type is required
    @1 = (struct @2)@3(*(long**)(@4+0x80));
  → @1 = @3(*(long**)(@4+0x80));
[5 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (@2*)@3[1];
  → @1 = *(@2**)(@3+1);
[5 worked, 0 didn't] indirection requires pointer operand ('X' invalid) (part of a line)
    *@1(
  → @1(
[5 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    (*@1+
  → (*(uint64_t*)@1+
[5 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    *(@1+
  → *(uint64_t*)(@1+
[5 worked, 1 didn't] member reference base type 'X' is not a structure or union (part of a line)
    @1.@2 = @3
  → @1[1] = @3
[4 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3();
  → @1 = @3();
[4 worked, 0 didn't] expected 'X' after expression
    @1 = (long*)std:: @2:: @2(@3, @4);
  → @1 = (long*)new std:: @2(@3, @4);
[4 worked, 0 didn't] expected 'X' after return statement
    return std:: @1:: @2(@3);
  → return;
[4 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = 0x3f800000;
  → @1[0] = 0x3f800000;
[4 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long*)@2(0xd0);
  → @1 = @2(0xd0);
[4 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long @1 = @2(0xd0);
  → unsigned long @1 = @2(0xd0);
[4 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    *@1 = @2.@3;
  → *@1 = @2[0];
[4 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    (@1);
  → (@1, 0);
[4 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\f" :
  → case 0x0C :
[4 worked, 1 didn't] used type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (struct @2)@3(
  → @1 = @3(
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3(@4);
  → *(unsigned char*)&@1 = (unsigned char)@3(@4);
[3 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @2:: @2(@2*this, @1*@3)
  → void @2(@2*this, @1*@3)
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    @1(@2.@3);
  → @1(*(unsigned char*)&@2);
[3 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@3.@4*(double)(@5+-1));
  → @1[0] = @2(@3*(double)(@5+-1));
[3 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4+1);
  → unsigned long long @1 = @2(@3, @4+1);
[3 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(0x14);
  → unsigned long @2 = @3(0x14);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1[0] = @2(@3, @4, @5, @6, @7, (long)@8[0], @9)
  → @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7, (long)@8[0], @9);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3(@4, @5, @6, @7, @8, *(int*)(@9+400)));
  → unsigned char @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, *(int*)(@9+400)));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X'
    unsigned char @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, *(int*)(@9+400)));
  → unsigned char @1 = @2(@3(@4, @5, @6, @7, @8, *(int*)(@9+400)));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3, @4, @5, @6, (long)@7, (@8*)@9);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7, (@8*)@9);
[3 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer
    @1 = @2(@3((@4)((@5)@6>>0x28), @7), @8);
  → @1 = @2(@3((int)((@5)@6>>0x28), @7), @8);
[3 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    long)@1[7]+0x20
  → long)(@1+7)+0x20
[3 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@3, (long*)&@4.@5);
  → @1 = @2(@3, (long*)@3[0x6c]+3);
[3 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[1
  → ((uint64_t*)(uintptr_t)(@1))[1
[3 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1;
  → uint64_t @1 = 0;
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1(@2, @3, @4, @5, @6, (long)@7[0], @8)
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)@7[0], @8);
[3 worked, 1 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = *(long*)((long)&@2.@3+@4);
  → @1 = *(long*)((long)@4[0x6a]+@4);
[3 worked, 1 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    @1[2
  → ((uint64_t*)(uintptr_t)(@1))[2
[3 worked, 1 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3

== candidate: 487
[85 worked, 206 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1 @2[
  → uint64_t @2[
[57 worked, 54 didn't] redefinition of 'X'
    @1 @2;
  → @1*@2;
[46 worked, 42 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2;
[24 worked, 21 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)();
  → @1 = @2();
[24 worked, 22 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    int @1;
  → uint64_t @1;
[16 worked, 15 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (@2*)@3(
  → @1 = @3(
[13 worked, 13 didn't] redefinition of 'X'
    @1 @2;
  → unsigned long*@2;
[11 worked, 9 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long @1;
  → uint64_t @1;
[11 worked, 11 didn't] too few arguments to function call, expected N, have N
    @1 = (float)@2();
  → float @1 = (float)@2(1);
[8 worked, 10 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2 = 0;
[7 worked, 8 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1;
[6 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required
    return(uint64_t)@1(&@2, &@3);
  → return @1(@2, @3);
[6 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    return(uint64_t)@1(&@2, &@3)
  → return @1(@2, @3)
[6 worked, 5 didn't] redefinition of 'X' (part of a line)
    @1 @2 =
  → @1*@2 =
[6 worked, 5 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long*@1;
  → uint64_t @1;
[5 worked, 4 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[16] = {0};@2(
[5 worked, 5 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    int @1;
  → uint64_t @1 = 0;
[5 worked, 5 didn't] redefinition of 'X'
    uint64_t @1;
  → unsigned long @1[16];
[5 worked, 7 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4, @5);
  → uint64_t @1 = @2(@3, @4, @5);
[4 worked, 3 didn't] redefinition of 'X'
    @1 @2;
  → @1*@2 = 0;
[4 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long*@1;
  → uint64_t*@1;
[4 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    unsigned long*@1
  → uint64_t*@1
[4 worked, 3 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → unsigned char @1[12] = {0};@2(
[4 worked, 4 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2 = 0;
[4 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1 = @2(@3);
[3 worked, 2 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5);
  → @1*@2 = @3(@4, @5);
[3 worked, 2 didn't] redefinition of 'X' (part of a line)
    @1 @2 =
  → unsigned long @2 =
[3 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = @2(@3(@4,
  → unsigned char @1 = @2(@3((unsigned char*)@4,
[3 worked, 2 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    long)&@1.@2+@3
  → long)@3[0x6a]+@3
[3 worked, 2 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1, @2(@3, 0, 8), @2(@3, 8, 8), @4);
  → @1, (const char*)@2(@3, 0, 8), @2(@3, 8, 8));
[3 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1 = 0;
[3 worked, 3 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    double @1;
  → uint64_t @1[16];
[3 worked, 3 didn't] too many arguments to function call, expected N, have N
    @1(@2, @3(@4, 0, 8), @3(@4, 8, 8), @5);
  → @1(@2, (const char*)@3(@4, 0, 8), @3(@4, 8, 8));
[3 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, "");
  → uint64_t @1 = @2(@3, "");
[3 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1[16] = {0};@2(@3);
[3 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2 = 0;
[2 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2(@3);
  → @1 = (int)@2(@3);
[2 worked, 0 didn't] must use 'X' tag to refer to type 'X'
    @1 @2;
  → struct @1 @2;
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → char @1[16];
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(*@4, @5);
  → @1 = @3(*@4, @5);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 0;
  → @1[2] = 0;
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4+1);
  → unsigned char @1[16];@2(@3, @4+1);
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3();
  → @1 = @3();
[2 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2();
  → return std:: @1:: @2();
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5);
  → unsigned char @1[16];@2(@3, @4, @5);
[2 worked, 0 didn't] expression is not assignable
    (void)@1 = @2();
  → (void)@2();
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3);
  → unsigned char @1[16];
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    , @1.@2, @1.@3, @4
  → , @1, @4
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3.@4;
  → @1[0] = @3[4];
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3<<0x20;
  → *(unsigned char*)&@1 = (unsigned char)(@3<<0x20);
[2 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];@3(@4, @5, @6);
  → uint64_t @2[16];@3(@4, @5, @6);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = (int*)@2((long*)&@3, @4.@5);
  → @1 = (int*)@2((long*)&@3, @4[0]);
[2 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → unsigned char @1[16];@2(&@3, &@4);
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union
    for(@1[0].@2 = 1;@3 = (int)@1[0], @4 = @5(), @3<(int)@4;
  → for(@1[0] = 1;@3 = (int)@1[0], @4 = @5(), @3<(@4);
[2 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0] = (@2*)@3(@1[0].@4, (int)@1[0]+1);
  → @1[0] = (@2*)@3(@1[0], (int)@1[0]+1);
[2 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @2.@3&0xffffffffffffff00);
  → @1(@2, 0, 8, @3&0xffffffffffffff00);
[2 worked, 0 didn't] no member named 'X' in 'X' (part of a line)
    8, @1.@2&
  → 8, @2&
[2 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5, @6);
  → @1*@2 = @3(@4, @5, @6);
[2 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@3;
  → @1[0] = @3;
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, 5);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, 5);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 1)
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 1);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, @8, @9, @10,
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9, @10,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3, @4, @5, @6, @7, &@8);
  → ```@1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = @2(@3,
  → ```@1 = @2((unsigned char*)@3,
[2 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    @1 = (@2*)*@3;
  → @1 = *(@2**)@3;
[2 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    (0x3ff0000000000000);
  → (0x3ff0000000000000, 0);
[2 worked, 0 didn't] redefinition of 'X'
    uint64_t @1;
  → uint64_t @1[1];
[2 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    @1(*(@2*)(@3+0x20));
  → ((uint64_t(*)())@1)(*(@2*)(@3+0x20));
[2 worked, 0 didn't] too few arguments to function call, single argument 'X' was not specified
    @1();
  → ((uint64_t(*)())@1)();
[2 worked, 0 didn't] too many arguments to function call, expected N, have N (part of a line)
    @1 = @2(@3
  → @1 = ((uint64_t(*)())@2)(@3
[2 worked, 0 didn't] too few arguments to function call, expected at least N, have N
    if((@1)&& (@2 = @3(@4), @2 = = 0)){
  → if((@1)&& (@2 = ((uint64_t(*)())@3)(@4), @2 = = 0)){
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → @1[16] = {0};@2(@3);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2(
  → @1[16] = {0};@2(
[2 worked, 1 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = @2((long)@3);
  → @1 = @2(@3);
[2 worked, 1 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1((long)@2)
  → @1(@2)
[2 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, @7, (long*)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long*)@8);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3);
  → unsigned char @1[16] = {0};@2(@3);
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    for(@1 = (@2*)*@3;@3 = @4, @1! = @5;
  → for(@1 = *(@2**)@3;@3 = @4, @1! = @5;
[2 worked, 1 didn't] too few arguments to function call, expected N, have N
    @1 = (long*)@2(0x3ff0000000000000);
  → @1 = (long*)@2(0x3ff0000000000000, 0);
[2 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    void*@1;
  → uint64_t*@1;
[2 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    void*@1
  → uint64_t*@1
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → unsigned char @1[16] = @2();
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = @2
  → unsigned char @1[16] = @2
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3);
  → unsigned char @1[12] = {0};@2(@3);
[2 worked, 1 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1[0] = @2(
  → unsigned char @1[8] = {0};@2(
[2 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    (**(@1**)(*@2+8))();
  → if(@2! = NULL){(**(@1**)(@2+8))();}
[2 worked, 2 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    long*@1;
  → uint64_t @1 = 0;
[2 worked, 2 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    (**(@1**)(*@2+0x18))(@2, @3, @4);
  → if(@2! = NULL){(**(@1**)(*@2+0x18))(@2, @3, @4);}
[2 worked, 2 didn't] too many arguments to function call, expected N, have N
    @1(@2, @3(@4, 0, 8), @3(@4, 8, 8), @5);
  → @1(@2, @3(@4, 0, 8), @3(@4, 8, 8));
[2 worked, 3 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3);
  → uint64_t @1[1] = {@2(@3)};
[2 worked, 3 didn't] too many arguments to function call, expected N, have N (part of a line)
    8), @1);
  → 8));
[2 worked, 4 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → uint64_t @1 = @2(@3, @4, @5, @6, @7, @8, @9);
[2 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2;
  → uint64_t @2[12];
[2 worked, 4 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1*@2;
  → uint64_t @2[12];
[2 worked, 5 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') (part of a line)
    @1 = @2(
  → uint64_t @1 = (uint64_t)@2(
[2 worked, 6 didn't] invalid operands to binary expression ('X' (aka 'X') and 'X' (aka 'X'))
    @1*@2;
  → uint64_t @2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(@4);
  → @2*@1 = @3(@4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x425378);
  → @1 = (void*)@2(0x425378);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → @1 = (unsigned char[16])@2();
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x42c348);
  → @1 = (void*)@2(0x42c348);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x444ba0);
  → @1 = (void*)@2(0x444ba0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x443540);
  → @1 = (void*)@2(0x443540);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = @3;
  → *(unsigned char*)&@1 = (unsigned char)@3;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, 0);
  → @1 = (unsigned char[16])@2(@3, @4, 0);
[1 worked, 0 didn't] expected 'X' after top level declarator
    @1 @2[16]@3(@4*@5, @6*@7);
  → @1 @2[16];@3(@4*@5, @6*@7);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → *(unsigned char*)&@1 = (unsigned char)@2(&@3, &@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43df20);
  → @1 = @3(0x43df20);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3((@4)@5, @6);
  → return @1;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3+0x54);
  → *(unsigned char*)(@3+0x54) = @2(@3+0x54);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3(@4);
  → return @1;
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    *(unsigned char*)(@1+0x54) = @2(@1+0x54);
  → *(unsigned char*)(@1+0x54) = (unsigned char)@2(@1+0x54);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x445250);
  → @1 = @3(0x445250);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x445280);
  → @1 = @3(0x445280);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4);
  → @1[16] = @2(@3, @4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2();
  → @1 = (int)@2();
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x4361f0);
  → @1 = @3(0x4361f0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x433368);
  → @1 = @3(0x433368);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(@3);
  → void*@1 = @2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43ccc0);
  → @1 = @3(0x43ccc0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x437670);
  → @1 = @3(0x437670);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (**(@2**)(*@3+0x228))(@3);
  → unsigned char @1[16];
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43a618);
  → @1 = @3(0x43a618);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3+0x78, @4);
  → unsigned char @1[16];@2(@3+0x78, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x43d8f0);
  → @1 = @3(0x43d8f0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x443070);
  → @1 = @3(0x443070);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3, @4);
  → unsigned char @1[16] = {0};@2((long)@3, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x444590);
  → @1 = @3(0x444590);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x443530);
  → @1 = @3(0x443530);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = 2;
  → *(unsigned char*)&@1 = (unsigned char)2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x442ad8);
  → @1 = @3(0x442ad8);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2)@3(0x444580);
  → @1 = @3(0x444580);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x4430e0);
  → @1 = (void*)@2(0x4430e0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(@3, 0.0, 0.0, 1.0, &@4);
  → @1 = (long)@2(@3, 0.0, 0.0, 1.0, &@4);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3);
  → unsigned char @1[16];@2(&@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (@3)(@4)@5;
  → @1[0] = (@3)(@4)@5;
[1 worked, 0 didn't] called object type 'X' (aka 'X') is not a function or function pointer
    @1 = @2();
  → @1 = @2;
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444480);
  → @1 = @3(0x444480);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444070);
  → @1 = @3(0x444070);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0xd0);
  → @1 = @3(0xd0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3(0x444490);
  → @1 = @3(0x444490);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[65544];(*(@2*)@3)();
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X'
    @1 = @2(@3);
  → (void*)@1 = @2(@3);
[1 worked, 0 didn't] expected 'X' after expression
    @1 = @2:: @3(*(@4*)(@5+0x20));
  → return @1;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4+1);
  → unsigned char @1[16] = {0};@2(@3, @4+1);
[1 worked, 0 didn't] expected 'X' after expression
    std:: @1:: @2((char)@3);
  → return(char)@3;
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, "", &@5, @6);
  → unsigned char @1[16];@2(@3, @4, "", &@5, @6);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    int @1 = @2(@3);
  → int @1 = (int)@2(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = @2(@3.@4*(double)(@5+-1));
  → @1[0] = @2(@3[0]*(double)(@5+-1));
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2();
  → @1[16] = {0};@2();
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4*9.0);
  → @1 = @2(@3[8]*9.0);
[1 worked, 0 didn't] expected expression
    @1[16] = {0};@2();
  → unsigned char @1[16];@2();
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (@2*)@3((long)@4);
  → @1 = @3((long)@4);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4341b8);
  → unsigned long long @1 = (unsigned long long)@2(0x4341b8);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, (@4*)(@5+0x37c));
  → @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(*(float*)(@3+0x3b8), (@4*)@5);
  → unsigned char @1[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned char @1[16];
  → unsigned char @1[12];
[1 worked, 0 didn't] expected expression
    @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
  → unsigned char @1[16] = {0};@2(@3, (@4*)(@5+0x37c));
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (short*)@2(
  → @1 = @2(
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x425378);
  → unsigned long long @1 = (unsigned long long)@2(0x425378);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1(@2, @3.@4, @3.@5, @6);
  → @1(@2, @3, @6);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (int)@2(
  → @1 = @2(
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (int*)@2((int*)&@3, (int*)&@4);
  → @1 = @2((int*)&@3, (int*)&@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (int*)@2(
  → @1 = @2(
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (**(@2**)(*@3+0x228))(@3);
  → unsigned char @1[16] = {0};(**(@2**)(*@3+0x228))(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1.@2 = @3[1];
  → @1[1] = @3[1];
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (@2)@3(
  → @1 = @3(
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2((@3*)@4);
  → @1 = (long)@2((@3*)@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (long)@2((@3*)@4);
  → @1 = @2(@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (long)@2((@3*)@4)
  → @1 = @2(@4)
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2(@3.@4);
  → @1 = @2(*(unsigned char*)&@3);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[65544] = {0};(*(@2*)@3)();
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable (part of a line)
    @1 = (*
  → unsigned char @1[65544] = {0};(*
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)0;
  → *(unsigned char*)&@1 = 0;
[1 worked, 0 didn't] variable has incomplete type 'X'
    void std:: @1:: @2(@3*@4)
  → void @2(@3*@4)
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[0], @3[8], @6[0], @6[8], @7[0], @7[8]);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = (*(@2*)@3)();
  → unsigned char @1[16] = {0};(*(@2*)@3)();
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    (@1.@2, @1.@3, @4
  → (@1, @4
[1 worked, 0 didn't] redefinition of 'X' (part of a line)
    unsigned char @1 =
  → void*@1 =
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    (@1.@2*(
  → (@1*(
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line)
    @1 = (long*)@2(
  → @1 = @2(
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (int)@3;
  → @1[0] = (int)@3;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = @2((long*)&@3, @4.@5);
  → @1 = @2((long*)&@3, @4[0]);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
    @1 @2[16];@3(@4, @5, @6, @7, @8, @9, @10);
  → uint64_t @2[16];@3(@4, @5, @6, @7, @8, @9, @10);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(@3, @4, &@5, &@6, @7);
  → unsigned char @1[16] = {0};@2(@3, @4, &@5, &@6, @7);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4282a0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4282a0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42eee0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42eee0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42ef00);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42ef00);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4421e0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4421e0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42eed0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42eed0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fd10);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fd10);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fe08);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fe08);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x42fcf0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x42fcf0);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1.@2 = 0x650002;
  → @1[0] = 0x650002;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444c78);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444c78);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444c88);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444c88);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[0], @3[1], @6[0], @6[1], @7[0]);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)0;
  → @1[1] = 0;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(&@2, @3.@4, @3.@5, @6.@4, @6.@5, @7.@4,
  → @1(&@2, @3[1], @3[2], @6[1], @6[2], @7[1],
[1 worked, 0 didn't] redefinition of 'X'
    unsigned char @1[16] = {0};@2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned long @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@3.@4, @3.@5, @6);
  → @1 = @2(&@3[0], &@3[8], @6);
[1 worked, 0 didn't] redefinition of 'X'
    unsigned char @1[16] = {0};@2(@3, @4, @5);
  → unsigned long @1[16];@2(@3, @4, @5);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
  → unsigned char @1[16];@2(@3, @4, @5, @6, @7, @8, @9);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];@2(@3, @4, @5);
  → unsigned char @1[16];@2(@3, @4, @5);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1 = @2(@1.@3, @1.@4, @5, @6);
  → @1 = @2(@1, @5, @6);
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433b0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433b0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433d0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433d0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433e0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433e0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x4433f0);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x4433f0);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444730);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444730);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x443410);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x443410);@3 = @1;
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x444460);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x444460);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = ((double)@3*@4*2.0*@5)/@6;
  → @1[1] = ((double)@3*@4*2.0*@5)/@6;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    *@1 = @2.@3;
  → *(unsigned char*)@1 = @2[0];
[1 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X'
    unsigned long long @1 = @2(0x425700);@3 = @1;
  → unsigned long long @1 = (unsigned long long)@2(0x425700);@3 = @1;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0] = (double)@2(@1[0].@3, @4);
  → @1[0] = (double)@2(@1[0], @4);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1(*(long*)(@2+0x8b90), @3[0].@4+@5);
  → @1(*(long*)(@2+0x8b90), @5);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(&@3, &@4);
  → @1[16] = {0};@2(&@3, &@4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    @1 = (float)@2(@3);
  → @1 = @2(@3);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (@2*)@3(@4);
  → @1 = (@2*)@3(@4, 0);
[1 worked, 0 didn't] cast to union type from type 'X' (aka 'X') not present in union
    @1 = (@2)@3(@4+0x54);
  → @1 = @3(@4+0x54);
[1 worked, 0 didn't] cast to union type from type 'X' (aka 'X') not present in union (part of a line)
    @1 = (@2)@3(
  → @1 = @3(
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = @3;
  → @1[0] = *(long*)(@1[0]+0x4);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = @3/@4;
  → @1[0] = *(long*)(@1[0]+0x4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(@2, 0, 12, @3.@4);
  → @1(@2, 0, 12, @3[4]);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2);
  → , @1[4]);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = (**(@2**)(*@3+0x228))(@3);
  → uint64_t @1 = (**(@2**)(*@3+0x228))(@3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (@3)(@4)@5;
  → @1[0] = (long)(@3)(@4)@5;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (@2
  → 0] = (long)(@2
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)("UTF-8");
  → @1 = @2("UTF-8");
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(@3, "Master dry/wet mix.");
  → @1 = @2(@3, "Master dry/wet mix", 0);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') (part of a line)
    @1, "Master dry/wet mix.");
  → @1, "Master dry/wet mix", 0);
[1 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @2.@3+1);
  → @1(@2, 0, 8, @3+1);
[1 worked, 0 didn't] no member named 'X' in 'X' (part of a line)
    8, @1.@2+
  → 8, @2+
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid)
    @1 = (*@2)(@3, @4, 0, 0, 0);
  → @1 = @2(@3, @4, 0, 0, 0);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = 0x640001
  → 0] = 0x640001
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = 0x650002;
  → @1[0] = 0x650002;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = 0x650002
  → 0] = 0x650002
[1 worked, 0 didn't] redefinition of 'X'
    @1 @2 = @3(@4, @5, @6, @7, @8, @9, @10);
  → @1*@2 = @3(@4, @5, @6, @7, @8, @9, @10);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = 1;@2 = (int)@3[0], @4 = @5(), @2<(int)@4;
  → 0] = 1;@2 = (int)@3[0], @4 = @5(), @2<(@4);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X'
    @1 = @2(0x3ff0000000000000, 8);
  → @1 = (long)@2(0x3ff0000000000000, 8);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    powf();
  → powf(1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    powf(1);
  → powf(1, 0);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1(@2, 4, 4, @2.@3+1);
  → @1(@2, 4, 4, @2+1);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    , @1.@2+1
  → , @1+1
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0] = @2(@1[0].@3, 0x3e800000);
  → @1[0] = @2(@1[0], 0x3e800000);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1, 0x3e800000
  → 0], 0x3e800000
[1 worked, 0 didn't] no member named 'X' in 'X'
    @1(@2, 0, 8, @3.@4);
  → @1(@2, 0, 8, @4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1[0].@2 = (uint32_t)((@3)>>32);
  → @1[0] = (uint32_t)((@3)>>32);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    0].@1 = (
  → 0] = (
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(0);
  → uint64_t @1[1] = {@2(0)};
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (aka 'X')
    @1 = @2(0.95, @3);
  → unsigned long @1 = @2(0.95, @3);
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (int)@2;
  → 0] = @2;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union
    @1[0].@2 = (int)@3[0]%100;
  → @1[0] = @3[0]%100;
[1 worked, 0 didn't] member reference base type 'X' is not a structure or union (part of a line)
    0].@1 = (int)@2[
  → 0] = @2[
[1 worked, 0 didn't] too few arguments to function call, expected at least N, have N (part of a line)
    0]);
  → 0], 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(0x3f800000, @2, @3, @4, @5);
  → @1(0x3f800000, @2, @3, @4, @5, 0);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1();
  → @1(1);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required
    return(uint64_t)@1(@2, @3-*(int*)(@2+0x198));
  → return @1(@2, @3-*(int*)(@2+0x198));
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1, @7, @8, @9, @10, 0);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 2, @7, @8, @9, @10, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 2, @7, @8, @9, @10, 0);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = (long*)@2(@3, @4, @5, @6, @7);
  → ```@1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line)
    @1 = (long*)@2(@3,
  → ```@1 = (long*)@2((unsigned char*)@3,
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3, @4, @5, @6, (int*)&@7);
  → unsigned char @1[16] = {0};@2(@3, @4, @5, @6, (int*)&@7);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = *@2;
  → unsigned char @1[16] = {0};
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(0.6060606, @3);
  → unsigned char @1[16] = {0};@2(0.6060606, @3);
[1 worked, 0 didn't] redefinition of 'X'
    @1 @2;
  → unsigned long @2[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    unsigned long @1[16];
  → uint64_t @1[16];
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line)
    unsigned long @1[
  → uint64_t @1[
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2();
  → unsigned char @1[1] = {0};@2();
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (double)@2(-@3);
  → @1 = @2(@3, 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (double)cos();
  → @1 = cos(0);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = (float)@2();
  → @1 = (float)@2(1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1 = @2(*(float*)(@3+0x28)-(float)*(int*)(@3+0x2c));
  → @1 = @2(*(float*)(@3+0x28)-(float)*(int*)(@3+0x2c), 1);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N (part of a line)
    0x2c));
  → 0x2c), 1);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3+0x180, @4);
  → unsigned char @1[1] = {0};@2(@3+0x180, @4);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3, @4);
  → unsigned char @1[1] = {0};@2(@3, @4);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
    char*@1;
  → uint64_t @1;
[1 worked, 0 didn't] integer constant expression must have integer type, not 'X'
    case"\x01" :
  → case'\x01' :
[1 worked, 0 didn't] too many arguments to function call, expected N, have N
    @1 = @2(@3, 0, @4, @5, 0x3f, 0, @6, (long)@7, &@8);
  → @1 = @2(@3, 0, @4, @6, 0x3f, 0, (long)@7, &@8);
[1 worked, 0 didn't] too few arguments to function call, expected N, have N
    @1(0x3ff0000000000000);
  → return @1(0x3ff0000000000000, 64);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1.@2 = (@3)@4;
  → @1[0] = (char)@4;
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union (part of a line)
    @1.@2 = (@3)@4
  → @1[0] = (char)@4
[1 worked, 0 didn't] indirection requires pointer operand ('X' invalid)
    *@1(@2, 8, 8, @3+0xdc4);
  → *(long*)(@1(@2, 8, 8, @3+0xdc4));
[1 worked, 0 didn't] indirection requires pointer operand ('X' invalid)
    *@1(@2, 8, 8, @3+0xdc4);
  → @1(@2, 8, 8, @3+0xdc4);
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    (**(@1**)(*(long*)((long)&@2.@3+*(long*)(*@4+0x428))+0x10))()
  → (**(@1**)(*(long*)((long)@4[0x428]+*(long*)(*@4+0x428))+0x10))()
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    (**(@1**)(*(long*)((long)&@2.@3+*(long*)(*@4+0x428))+0x18))()
  → (*(@1**)(*(long*)(@4[0x428]+*(long*)(*@4+0x428))+0x18))()
[1 worked, 0 didn't] member reference base type 'X' (aka 'X') is not a structure or union
    @1 = (@2*)@3(@4, (long*)((long)&@5.@6+2));
  → @1 = (@2*)@3(@4, (long*)((long)@4[0x6c]+2));
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (long*)((long)@2[0x68]+2);
  → @1 = (long*)((long)@2+0x68*2);
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    @1 = (@2*)((long)@3[0x68]+3);
  → @1 = (@2*)((long)(@3+0x68)+3);
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector
    if((((int)@1 = = 0)&& (@2[0x68]+3< = @3))&&
  → if((((int)@1 = = 0)&& ((long*)(@2+0x68)+3< = @3))&&
[1 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line)
    &(@1[0x68]+3
  → &((long*)(@1+0x68)+3
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2((long)@3);
  → unsigned char @1[16] = {0};@2((long)@3);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1 = @2(@3, @4, @5, @6, @7, @8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, @8);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X'
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long*)@8);
  → @1((unsigned char*)@2, @3, @6, @7, (long*)@8);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' (part of a line)
    @1, @2, @3, @4,
  → @1, @4,
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X'
    @1(@2, @3, @4, @5, @6, 0, 2, 0, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 0, 2, 0, 0);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1[0] = @2(@3, @4, @5, @6, (int*)&@7);
  → unsigned char @1[8] = {0};@2(@3, @4, @5, @6, (int*)&@7);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(0.25, @3);
  → unsigned char @1[16] = {0};@2(0.25, @3);
[1 worked, 0 didn't] array type 'X' (aka 'X') is not assignable
    @1 = @2(0.6060606, @3);
  → unsigned char @1[12] = {0};@2(0.6060606, @3);

== retired: 159
[5940 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (void*)@2(@3);
[5922 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(@3);
  → @1 = @2(@3);
[4620 worked, 1 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (long)@2(@3);
[4434 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3);
  → @1 = @2(@3);
[1935 worked, 1 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2();
  → @1 = (long)@2();
[1905 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2();
  → @1 = @2();
[771 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@1);
  → @1 = (long)@2(@1);
[744 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@1);
  → @1 = @2(@1);
[401 worked, 177 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1(@2,
  → @1((unsigned char*)@2,
[230 worked, 135 didn't] passing 'X' to parameter of incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1((unsigned char*)@2,
  → @1(@2,
[138 worked, 39 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6);
  → @1((unsigned char*)@2, @3, @4, @5, @6);
[86 worked, 35 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6);
  → @1(@2, @3, @4, @5, @6);
[77 worked, 27 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    return(uint64_t)@1(
  → return @1(
[65 worked, 15 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    return @1(
  → return(uint64_t)@1(
[35 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    void*@1 = @2((@3*)(@4+0x88));
  → unsigned char @1 = @2((@3*)(@4+0x88));
[33 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x43d890);
  → @1 = (void*)@2(0x43d890);
[33 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x436f30);
  → @1 = (void*)@2(0x436f30);
[33 worked, 8 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7);
[32 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long @1 = @2(0xd0);
  → unsigned long*@1 = @2(0xd0);
[31 worked, 0 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    unsigned char @1 = @2((@3*)(@4+0x88));
  → void*@1 = @2((@3*)(@4+0x88));
[30 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long*@1 = @2(0xd0);
  → unsigned long @1 = @2(0xd0);
[29 worked, 6 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7);
[24 worked, 6 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 0);
[24 worked, 21 didn't] assigning to 'X' from incompatible type 'X' (aka 'X') — retired: it and its opposite only undo each other
    @1 = @2(@3, @4);
  → uint64_t @1 = @2(@3, @4);
[23 worked, 4 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 1);
[19 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4);
  → @1 = (long)@2(@3, @4);
[19 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5);
  → return @1(@2, @3, @4, @5);
[19 worked, 7 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7);
  → @1(@2, @3, @4, @5, @6, @7);
[18 worked, 5 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 0);
  → @1(@2, @3, @4, @5, @6, 0);
[17 worked, 1 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5);
  → return(uint64_t)@1(@2, @3, @4, @5);
[16 worked, 3 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3);
  → return(uint64_t)@1(@2, @3);
[16 worked, 4 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3);
  → return @1(@2, @3);
[15 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, @6, @7);
  → return @1(@2, @3, @4, @5, @6, @7);
[14 worked, 2 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5, @6, @7);
  → return(uint64_t)@1(@2, @3, @4, @5, @6, @7);
[14 worked, 13 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    uint64_t @1;
  → unsigned long @1;
[12 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)@8);
[12 worked, 3 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(&@2, &@3);
  → return @1(&@2, &@3);
[11 worked, 1 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(&@2, &@3);
  → return(uint64_t)@1(&@2, &@3);
[10 worked, 5 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7);
  → @1 = @2(@3, @4, @5, @6, @7);
[9 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (short*)@2(@3);
  → @1 = @2(@3);
[9 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x443fc0);
  → @1 = (int)@2(0x443fc0);
[9 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, 2, 1, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, 2, 1, 1);
[9 worked, 3 didn't] assigning to 'X' from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1 = @2(
  → @1 = (long)@2(
[8 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, 1);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, 1);
[8 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, (long)@7);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7);
[8 worked, 4 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, *(long*)(@6+@7));
  → @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7));
[7 worked, 0 didn't] initializing 'X' with an expression of incompatible type 'X' — retired: it and its opposite only undo each other
    long @1 = @2(@3, @4);
  → int @1 = (int)@2(@3, @4);
[7 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (long*)0x0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long*)0x0);
[7 worked, 3 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7));
  → @1(@2, @3, @4, @5, *(long*)(@6+@7));
[6 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2();
  → @1 = @2();
[6 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4);
  → return @1(@2, @3, @4);
[6 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
[6 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, &@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
[6 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long @1;
  → uint64_t @1;
[6 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6);
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6);
[6 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 1);
  → @1(@2, @3, @4, @5, @6, 1);
[6 worked, 4 didn't] redefinition of 'X' — retired: it and its opposite only undo each other
    uint64_t @1;
  → unsigned long*@1;
[5 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(0x42a960);
  → @1 = @2(0x42a960)&0xFFFFFFFFFFFFFFFF;
[5 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @3, @4);
  → return @1(@2, @3, @3, @4);
[5 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, (int*)&@8);
  → @1 = @2(@3, @4, @5, @6, @7, (int*)&@8);
[5 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, 1);
  → @1 = @2(@3, @4, @5, @6, @7, 1);
[5 worked, 0 didn't] assigning to 'X' from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    ] = @1(
  → ] = (unsigned char)@1(
[5 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, @7, (int*)&@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, @7, (int*)&@8);
[5 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, @7, &@8);
  → @1 = @2(@3, @4, @5, @6, @7, &@8);
[5 worked, 2 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3+0x180, @4);
  → @1[0] = (unsigned char)@2(@3+0x180, @4);
[4 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8));
[4 worked, 0 didn't] subscripted value is not an array, pointer, or vector (part of a line) — retired: it and its opposite only undo each other
    @1[1] = 0
  → *(@1+1) = 0
[4 worked, 1 didn't] subscripted value is not an array, pointer, or vector — retired: it and its opposite only undo each other
    @1[1] = 0;
  → *(@1+1) = 0;
[3 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @3, @4);
  → return(uint64_t)@1(@2, @3, @3, @4);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (long)(@7+0x2a));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (long)(@7+0x2a));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (long)(@7+0x2a));
  → @1(@2, @3, @4, @5, @6, (long)(@7+0x2a));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, 0);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, 0);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, @6, @7, @8);
  → return(uint64_t)@1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    return(uint64_t)@1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
  → return(uint64_t)@1(@2, @3, @4, @5, @6, @7, @8);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
  → @1(@2, @3, @4, @5, @6, (@7)*(@8*)((long)@9+0x27c));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
  → @1(@2, @3, @4, @5, @6, (@7)*(@8*)(@9+0x27c));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6, @7);
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6, @7);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8,
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8,
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, @9);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6, @7);
  → @1(@2, @3, @4, @5, (long)@6, @7);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, *@6, @6[1], *@7, @7[1]);
  → @1 = @2((unsigned char*)@3, @4, @5, *@6, @6[1], *@7, @7[1]);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, @5, @6, (@7*)&@8);
  → @1 = @2((unsigned char*)@3, @4, @5, @6, (@7*)&@8);
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, (int*)&@8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (int*)&@8));
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (int*)&@8));
  → @1 = @2(@3(@4, @5, @6, @7, (int*)&@8));
[3 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, &@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, &@7);
[3 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, (long)@7);
  → @1 = @2(@3, @4, @5, @6, (long)@7);
[3 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1[0] = (unsigned char)@2(@3+0x180, @4);
  → @1[0] = @2(@3+0x180, @4);
[3 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    ] = (unsigned char)@1(
  → ] = @1(
[3 worked, 1 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, 2, 1, 1);
  → @1(@2, @3, @4, @5, @6, @7, 2, 1, 1);
[3 worked, 1 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, (long)@6,
  → @1((unsigned char*)@2, @3, @4, @5, (long)@6,
[3 worked, 1 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (long*)0x0);
  → @1(@2, @3, @4, @5, @6, (long*)0x0);
[3 worked, 2 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7)@8);
  → @1(@2, @3, @4, @5, @6, (@7)@8);
[3 worked, 2 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, 0, 1);
  → @1((unsigned char*)@2, @3, @4, @5, @6, 0, 1);
[2 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2();
  → @1 = (void*)@2();
[2 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4);
  → return(uint64_t)@1(@2, @3, @4);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, 0);
  → @1(@2, @3, @4, @5, @6, @7, @8, 0);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8));
  → @1 = @2(@3(@4, @5, @6, @7, @8));
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8,
  → @1 = @2(@3(@4, @5, @6, @7, @8,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9);
  → @1(@2, @3, @4, @5, @6, @7, @8, @9);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, *@6, @6[1], *@7, @7[1]);
  → @1 = @2(@3, @4, @5, *@6, @6[1], *@7, @7[1]);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, @5, @6, (@7*)&@8);
  → @1 = @2(@3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (int*)@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (int*)@7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, &@7);
  → @1(@2, @3, @4, @5, @6, &@7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (@7*)&@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (@7*)&@8);
  → @1(@2, @3, @4, @5, @6, (@7*)&@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, @8, @9,
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8, @9,
  → @1(@2, @3, @4, @5, @6, @7, @8, @9,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, @7, (long)@8);
  → @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long)@8);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, (long)@8);
  → @1(@2, @3, @4, @5, @6, @7, (long)@8);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, @8, @9, @10, @11,
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, @9, @10, @11,
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, @8, @9, @10, @11,
  → @1 = @2(@3(@4, @5, @6, @7, @8, @9, @10, @11,
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3, @4, @5, @6, @7);
  → @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2((unsigned char*)@3, @4, @5, @6, @7);
  → @1[0] = @2(@3, @4, @5, @6, @7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, @6, (int*)&@7);
  → @1((unsigned char*)@2, @3, @4, @5, @6, (int*)&@7);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (int*)&@7);
  → @1(@2, @3, @4, @5, @6, (int*)&@7);
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1(@2, @3, @4, @5, *(long*)(@6+@7),
  → @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7),
[2 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, @4, (@5*)&@6, 1);
  → @1 = @2((unsigned char*)@3, @4, (@5*)&@6, 1);
[2 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, 0, 1);
  → @1(@2, @3, @4, @5, @6, 0, 1);
[2 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(@2, @3, @4, @5, &@6, 1);
  → return @1(@2, @3, @4, @5, &@6, 1);
[1 worked, 0 didn't] invalid operands to binary expression ('X' and 'X') — retired: it and its opposite only undo each other
    @1 = @2(0x42a960)&0xFFFFFFFFFFFFFFFF;
  → @1 = @2(0x42a960);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3);
  → @1 = (short*)@2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(0x43d890);
  → @1 = @2(0x43d890);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (void*)@2(0x436f30);
  → @1 = @2(0x436f30);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3, @4);
  → @1 = @2(@3, @4);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (int)@2(0x443fc0);
  → @1 = @2(0x443fc0);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    unsigned long @1 =
  → unsigned long*@1 =
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    int @1 = (int)@2(@3, @4);
  → long @1 = @2(@3, @4);
[1 worked, 0 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') (part of a line) — retired: it and its opposite only undo each other
    unsigned long*@1 =
  → unsigned long @1 =
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required (part of a line) — retired: it and its opposite only undo each other
    @1 = (long)@2(
  → @1 = @2(
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3, 0);
  → @1 = (long)@2(@3, 0);
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' — retired: it and its opposite only undo each other
    @1[0] = @2(@3);
  → @1[0] = (unsigned long)@2(@3);
[1 worked, 0 didn't] assigning to 'X' from incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@1, @3);
  → @1 = (long)@2(@1, @3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@3, 0);
  → @1 = @2(@3, 0);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1[0] = (unsigned long)@2(@3);
  → @1[0] = @2(@3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    @1 = (long)@2(@1, @3);
  → @1 = @2(@1, @3);
[1 worked, 0 didn't] operand of type 'X' where arithmetic or pointer type is required — retired: it and its opposite only undo each other
    return(uint64_t)@1(&@2);
  → return @1(&@2);
[1 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(&@2);
  → return(uint64_t)@1(&@2);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6);
  → @1(@2, @3, @4, @5, (long)@6);
[1 worked, 0 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) — retired: it and its opposite only undo each other
    *(@1+1) = 0;
  → @1[1] = 0;
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, (int*)@7);
  → @1(@2, @3, @4, @5, @6, (int*)@7);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, *(long*)(@6+@7),
  → @1(@2, @3, @4, @5, *(long*)(@6+@7),
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, @6, @7, @8);
  → @1(@2, @3, @4, @5, @6, @7, @8);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = (long*)@2(@3, @4, @5, @6, @7);
  → @1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = (long*)@2((unsigned char*)@3, @4, @5, @6, @7);
  → @1 = (long*)@2(@3, @4, @5, @6, @7);
[1 worked, 0 didn't] passing 'X' (aka 'X') to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3(@4, @5, @6, @7, (long)@8));
  → @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (long)@8));
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2(@3((unsigned char*)@4, @5, @6, @7, (long)@8));
  → @1 = @2(@3(@4, @5, @6, @7, (long)@8));
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1 = @2((unsigned char*)@3, @4, (@5*)&@6, 1);
  → @1 = @2(@3, @4, (@5*)&@6, 1);
[1 worked, 0 didn't] passing 'X' to parameter of incompatible type 'X' — retired: it and its opposite only undo each other
    @1((unsigned char*)@2, @3, @4, @5, (long)@6,
  → @1(@2, @3, @4, @5, (long)@6,
[1 worked, 0 didn't] assigning to 'X' (aka 'X') from incompatible type 'X' (part of a line) — retired: it and its opposite only undo each other
    @1(@2,
  → @1((unsigned char*)@2,
[1 worked, 0 didn't] returning 'X' from a function with incompatible result type 'X' (aka 'X') — retired: it and its opposite only undo each other
    return @1(@2, @3, @4, @5, &@6, 1);
  → return(uint64_t)@1(@2, @3, @4, @5, &@6, 1);
[1 worked, 1 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line) — retired: it and its opposite only undo each other
    *(@1+1) = 0
  → @1[1] = 0
[1 worked, 1 didn't] redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X') — retired: it and its opposite only undo each other
    unsigned long*@1;
  → uint64_t @1;
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' — retired: it and its opposite only undo each other
    uint64_t @1 = @2(@3, @4);
  → @1 = @2(@3, @4);
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (part of a line)
    uint64_t @1 =
  → @1 =
[1 worked, 5 didn't] indirection requires pointer operand ('X' (aka 'X') invalid) (part of a line)
    @1 = (*@2)(@3
  → @1 = @2(@3
[1 worked, 5 didn't] redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X') (part of a line)
    @1 @2[
  → unsigned long long @2[
[1 worked, 5 didn't] integer constant expression must have integer type, not 'X'
    case"" :
  → case'\x01' :
```

## build/ideas.txt

```
Ideas the model proposed for kinds of error many functions share, and what
happened to each (newest last). 'adopted' ones are in the build.

== array type 'X' (aka 'X') is not assignable
   24 idea(s), 0 adopted; parked until something changes (or run 8)
   #8 [rejected] rewrite: @1 = @2 ( @3 ) ;  ->  @1 = @2 ( @3 , 0 ) ;
        tested on 7: 0 better, 0 worse
   #9 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #10 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #44 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #45 [repeat] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        same as #44
   #46 [rejected] rewrite: @1 = @2 ( 0.6060606 , @3 ) ;  ->  @1 [ 0 ] = @2 ( 0.6060606 , @3 ) [ 0 ] ;
        tested on 1: 0 better, 0 worse
   #65 [no effect] rewrite: * @1 = & @2 ;  ->  * @1 = ( undefined8 * ) & @2 ;
        its 'before' text isn't in any failing line of the examples
   #66 [no effect] rewrite: * @1 = @2 ( @3 ) ;  ->  * @1 = @2 ( @3 ) [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #67 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #87 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #88 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #89 [repeat] flag: -Wno-error=invalid-assignment
        same as #87
   #108 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( @ 3 ) [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #109 [repeat] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( @ 3 ) [ 0 ] ;
        same as #108
   #110 [no effect] rewrite: * @ 1 = ( undefined8 * ) & @ 2 ;  ->  * @ 1 = ( undefined1 * ) & @ 2 ;
        its 'before' text isn't in any failing line of the examples
   #126 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = & @ 2 [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #127 [no effect] rewrite: * @ 1 = ( undefined8 * ) & @ 2 ;  ->  * @ 1 = ( undefined1 * ) & @ 2 [ 0 ] ;
        its 'before' text isn't in any failing line of the examples
   #128 [rejected] declare undefined1_ptr: unsigned char * undefined1_ptr ( void ) ;
        shared.h declares no function undefined1_ptr
   #142 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #143 [repeat] flag: -Wno-error=invalid-assignment
        same as #142
   #144 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ;  ->  * @ 1 = @ 2 ( 0 ) ; * ( ( undefined8 * ) & @ 1 ) = @ 3 ;
        its 'before' text isn't in any failing line of the examples
   #164 [rejected] flag: -Wno-error=invalid-assignment
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #165 [repeat] flag: -Wno-error=invalid-assignment
        same as #164
   #166 [no effect] rewrite: * @ 1 = @ 2 ( @ 3 ) ; -> * @ 1 = & @ 2 [ 0 ] ;  ->  * @ 1 = @ 2 ( 0 , sizeof ( undefined1 [ 0 ] ) ) ;
        its 'before' text isn't in any failing line of the examples

== indirection requires pointer operand ('X' (aka 'X') invalid)
   23 idea(s), 0 adopted; parked until something changes (or run 8)
   #29 [rejected] typedef: typedef unsigned long long uint64_t ;
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #30 [rejected] flag: -Wno-error=invalid-operand
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #31 [rejected] rewrite: * @1 ! = 0  ->  ( @1 = = ( undefined8 * ) - 1 ) | | * @1 ! = 0
        tested on 1: 0 better, 1 worse
   #53 [rejected] rewrite: * @1 ! = 0 ;  ->  * @1 > 0 ;
        tested on 1: 0 better, 0 worse
   #54 [no effect] rewrite: * * ( code * ) ( * @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;  ->  * * ( code * ) * ( @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;
        its 'before' text isn't in any failing line of the examples
   #71 [no effect] rewrite: * @ 1 ! = 0  ->  * @ 1 > 0
        its 'before' text isn't in any failing line of the examples
   #72 [rejected] rewrite: * * ( code * * ) ( * @1 + 0x20 ) ) ( @1 , @2 , @3 ) ;  ->  * * ( code * * ) ( @1 + 0x20 , @1 , @2 , @3 ) ;
        tested on 1: 0 better, 0 worse
   #73 [rejected] rewrite: * @1 ! = 0 ;  ->  * ( long * ) @1 ! = 0 ;
        tested on 1: 0 better, 0 worse
   #93 [rejected] rewrite: * @1 ! = 0  ->  * @1 > 0
        tested on 1: 0 better, 0 worse
   #94 [no effect] rewrite: * @ 1 ! = 0 ;  ->  * @ 1 > 0 ;
        its 'before' text isn't in any failing line of the examples
   #95 [rejected] typedef: * local_8 = local_8 + 1 ;
        tested on 8: 0 better, 8 worse, 2 compiling function(s) broke
   #113 [no effect] rewrite: * @1 = @2 ;  ->  @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #114 [no effect] rewrite: * * ( code * ) ( * @1 + 0x18 ) ) ( @1 , @2 , @3 ) ;  ->  * ( code * ) * ( * ( @1 + 0x18 ) ) ( * @1 , @2 , @3 ) ;
        its 'before' text isn't in any failing line of the examples
   #115 [rejected] flag: -Wno-error=invalid-operand
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #132 [no effect] rewrite: * @1 = @1 + 1 ;  ->  * ( long * ) @1 + + ;
        its 'before' text isn't in any failing line of the examples
   #133 [no effect] rewrite: * @ 1 > 0 ;  ->  * ( long * ) @ 1 > 0 ;
        its 'before' text isn't in any failing line of the examples
   #134 [rejected] declare _void_p_void_p: typedef void * _void_p_void_p ( void * , void * ) ;
        shared.h declares no function _void_p_void_p
   #152 [rejected] declare FUN_00001a3c: void FUN_00001a3c ( gh16 , double , undefined8 , double , long * ) ;
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #153 [no effect] rewrite: * * ( code * )  ->  ( code * )
        its 'before' text isn't in any failing line of the examples
   #154 [no effect] rewrite: * @1 = @2 ;  ->  @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #173 [no effect] rewrite: * @1 = @2 ;  ->  * @1 = ( long * ) @2 ;
        its 'before' text isn't in any failing line of the examples
   #174 [no effect] rewrite: * * ( code * ) ( * @1 + 0x20 ) )  ->  * * ( code * ) ( * ( long * ) ( @1 + 0x20 ) ) )
        its 'before' text isn't in any failing line of the examples
   #175 [rejected] flag: -Wno-error=indirect-assignment
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke

== member reference base type 'X' (aka 'X') is not a structure or union
   32 idea(s), 0 adopted; parked until something changes (or run 9)
   #5 [rejected] typedef: typedef uint8_t [ 32 ] magic_buffer ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #6 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #7 [repeat] typedef: typedef uint8_t [ 32 ] magic_buffer ;
        same as #5
   #37 [no effect] rewrite: ( long ) ( ( long ) & @1 . magic + 1 )  ->  ( long ) ( & @1 . magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #38 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #39 [repeat] flag: -Wno-error=invalid-offsetof
        same as #38
   #60 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #61 [no effect] rewrite: ( long ) ( & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #84 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #85 [repeat] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        same as #84
   #86 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #106 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #107 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1L )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #123 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #124 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1L )  ->  ( long ) ( & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #125 [rejected] typedef: typedef char * string ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #140 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #141 [rejected] flag: -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #161 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1  ->  ( long ) ( ( long ) & @ 1. magic + 1L
        its 'before' text isn't in any failing line of the examples
   #162 [no effect] rewrite: ( long ) ( ( long ) & @ 1. magic + 1 )  ->  ( long ) ( ( long ) & @ 1. magic + 1L )
        its 'before' text isn't in any failing line of the examples
   #163 [rejected] typedef: typedef uint8_t string [ sizeof ( uint64_t ) ] ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #180 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #181 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #182 [repeat] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        same as #181
   #186 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #187 [repeat] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        same as #186
   #188 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #189 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20)" -> "(long)param_6 + *(unsigned long *)(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #193 [no effect] rewrite "(long)param_6 + *(long *)(lVar7 + 0x20) + 1" -> "(long)param_6 + (long)*(lVar7 + 0x20)"
        its 'before' text isn't in any failing line of the examples
   #194 [no effect] rewrite "*pbVar2 = (byte *)((long)&GD_MACH_HEADER.magic + 1);" -> "*pbVar2 = (byte *)((long)&GD_MACH_HEADER.magic + 1L);"
        its 'before' text isn't in any failing line of the examples
   #198 [rejected] flag -Wno-error=invalid-offsetof
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #199 [rejected] header line typedef uint8_t * byte;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke

== operand of type 'X' where arithmetic or pointer type is required
   37 idea(s), 0 adopted; parked until something changes (or run 9)
   #11 [rejected] flag: -Wno-error=invalid-integer
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #12 [rejected] declare FUN_0013cf80_new: struct streambuf * FUN_0013cf80_new ( struct streambuf * param_1 ) ;
        shared.h declares no function FUN_0013cf80_new
   #13 [repeat] declare FUN_0013cf80_new: struct streambuf * FUN_0013cf80_new ( struct streambuf * param_1 ) ;
        same as #12
   #40 [no effect] rewrite: * @1 * @2 + @3 * @4  ->  ( uint64_t ) ( ( int ) * @1 * @2 + ( int ) @3 * @4 )
        its 'before' text isn't in any failing line of the examples
   #41 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) ) * ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #42 [rejected] declare FUN_0014c8e0_new: uint64_t FUN_0014c8e0_new ( gh16 param_1 , undefined39 param_2 ) ;
        shared.h declares no function FUN_0014c8e0_new
   #62 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) * 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #63 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #64 [rejected] declare FUN_00141c54_new: int FUN_00141c54_new ( uint64_t * param_1 , uint64_t * param_2 ) ;
        shared.h declares no function FUN_00141c54_new
   #81 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #82 [repeat] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        same as #81
   #83 [rejected] flag: -Wno-error=int-conversion
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #103 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #104 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #103
   #105 [no effect] rewrite: * @ 1 * @ 2 + @ 3 * @ 4  ->  ( uint64_t ) ( ( int ) @ 1 * @ 2 + ( int ) @ 3 * @ 4 )
        its 'before' text isn't in any failing line of the examples
   #120 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #121 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #120
   #122 [rejected] flag: -Wno-error=int-conversion
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #137 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #138 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #137
   #139 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #137
   #158 [rejected] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        shared.h declares no function SoftwareBreakpoint
   #159 [repeat] declare SoftwareBreakpoint: code * SoftwareBreakpoint ( int param_1 , int param_2 ) ;
        same as #158
   #160 [rejected] typedef: typedef void ( * code ) ( void ) ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #176 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #177 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 - *(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFF
        tested on 1: 0 better, 0 worse
   #178 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #179 [rejected] rewrite "(uint64_t)FUN_00141960(param_2,param_3,param_4,param_5,param_6,param_7);" -> "(uint64_t)FUN_00141960((int)(param_2), (int)(param_3), (int)(param_4), (i
        tested on 2: 0 better, 0 worse
   #183 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #184 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFFF
        tested on 1: 0 better, 0 worse
   #185 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #190 [no effect] rewrite "*pdVar2 *local_48 + dVar5*dVar4" -> "(uint64_t)((int)*pdVar2 * local_48 + (int)dVar5 *dVar4)"
        its 'before' text isn't in any failing line of the examples
   #191 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1,param_2 - (*(int *)(param_1 + 0x198)) & 0xFFFFFF
        tested on 1: 0 better, 0 worse
   #192 [rejected] header line typedef struct __float2 float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #195 [rejected] header line typedef float __float2;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #196 [rejected] rewrite "(uint64_t)FUN_000ca8cc(param_1,param_2 -*(int *)(param_1 + 0x198))" -> "(uint64_t)FUN_000ca8cc(param_1, (int)(param_2 - (*(int *)(param_1 + 0x198))));"
        tested on 1: 0 better, 0 worse
   #197 [rejected] flag -Wno-error=invalid-constexpr-expression
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' (aka 'X') to parameter of incompatible type 'X'
   21 idea(s), 0 adopted; parked until something changes (or run 8)
   #1 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #2 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #1
   #3 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #4 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #35 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #36 [repeat] flag: -Wno-error=implicit-int
        same as #35
   #58 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #59 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #78 [rejected] flag: -Wno-error=implicit-int
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #79 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #80 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( gh16 [ 8 ] )
        its 'before' text isn't in any failing line of the examples
   #100 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #101 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #100
   #102 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #118 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #119 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #118
   #135 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #136 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #135
   #155 [no effect] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        its 'before' text isn't in any failing line of the examples
   #156 [repeat] rewrite: ( undefined1 [ 16 ] )  ->  ( unsigned char [ 16 ] )
        same as #155
   #157 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' to parameter of incompatible type 'X'
   6 idea(s), 0 adopted; parked until something changes (or run 6)
   #149 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #150 [rejected] typedef: typedef unsigned char gh16 ;
        tested on 9: 0 better, 9 worse, 2 compiling function(s) broke
   #151 [repeat] typedef: typedef unsigned char gh16 ;
        same as #150
   #170 [no effect] rewrite: float @1 = ( float ) powf ( @2 , 0x3e4ccccd ) ;  ->  float @1 = ( float ) pow ( @2 , 0x3e4ccccd ) ;
        its 'before' text isn't in any failing line of the examples
   #171 [no effect] rewrite: @1 = fmod ( @2 , ( double ) ( long ) * ( int * ) ( @3 + 0x298 ) + - 1.0 ) ;  ->  @1 = fmod ( @2 , ( double ) ( long ) * ( int * ) ( @3 + 0x298 ) ) ;
        its 'before' text isn't in any failing line of the examples
   #172 [rejected] flag: -Wno-error=invalid-const-ref
        tested on 10: 0 better, 0 worse, 0 compiling function(s) broke

== passing 'X' to parameter of incompatible type 'X' (aka 'X')
   24 idea(s), 0 adopted; parked until something changes (or run 8)
   #23 [rejected] flag: -Wno-error=invalid-constexpr-expression
        tested on 14: 0 better, 0 worse, 0 compiling function(s) broke
   #24 [rejected] declare FUN_000037fc: undefined8 FUN_000037fc ( undefined8 )
        tested on 14: 0 better, 14 worse, 2 compiling function(s) broke
   #25 [rejected] typedef: typedef uint64_t gh16 ;
        tested on 14: 0 better, 14 worse, 2 compiling function(s) broke
   #50 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 2: 0 better, 0 worse
   #51 [no effect] rewrite: @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( @ 6 , @ 7 ) ) ;  ->  @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , ( undefined1 ) CONCAT44 ( @ 6 , @
        its 'before' text isn't in any failing line of the examples
   #52 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 11: 0 better, 0 worse, 0 compiling function(s) broke
   #68 [rejected] rewrite: CONCAT44 ( @1 , @2 )  ->  CONCAT44 ( ( undefined1 ) @1 , @2 )
        tested on 2: 0 better, 0 worse
   #69 [rejected] rewrite: @1 = @2 ( @3 , @4 , @5 ) ;  ->  @1 = @2 ( ( undefined8 ) @3 , @4 , @5 ) ;
        tested on 3: 0 better, 0 worse
   #70 [rejected] declare FUN_000052cb8: void FUN_000052cb8 ( undefined1 * param_1 , undefined8 local_a8 , undefined8 unused_param ) ;
        shared.h declares no function FUN_000052cb8
   #90 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 11: 0 better, 0 worse, 0 compiling function(s) broke
   #91 [repeat] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        same as #90
   #92 [rejected] declare FUN_00052cb8: void FUN_00052cb8 ( undefined1 * param_1 , undefined8 local_a8 , undefined8 unused_param ) ;
        tested on 11: 0 better, 0 worse, 1 compiling function(s) broke
   #111 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #112 [rejected] declare GH16: undefined8 GH16 ( undefined1 param_1 ) ;
        shared.h declares no function GH16
   #129 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #130 [repeat] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        same as #129
   #131 [rejected] typedef: typedef unsigned long long gh16 ;
        tested on 12: 0 better, 12 worse, 2 compiling function(s) broke
   #145 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #146 [rejected] declare GH16: undefined8 GH16 ( undefined1 param_1 ) ;
        shared.h declares no function GH16
   #147 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #148 [rejected] declare GH16: undefined8 GH16 ( undefined8 param_1 ) ;
        shared.h declares no function GH16
   #167 [rejected] rewrite: @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , CONCAT44 ( @6 , @7 ) ) ;  ->  @1 ( 0x3f800000 , @2 , @3 , @4 , @5 , ( undefined1 ) CONCAT44 ( @6 , @7 ) ) ;
        tested on 3: 0 better, 0 worse
   #168 [rejected] flag: -Wno-error=integral-promotion-incompatible-pointer-type
        tested on 12: 0 better, 0 worse, 0 compiling function(s) broke
   #169 [no effect] rewrite: @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( @ 6 , @ 7 ) ) ;  ->  @ 1 ( 0x3f800000 , @ 2 , @ 3 , @ 4 , @ 5 , CONCAT44 ( ( undefined1 ) @ 6 , (
        its 'before' text isn't in any failing line of the examples

== redefinition of 'X'
   2 idea(s), 0 adopted; parked until something changes (or run 4)
   #19 [rejected] typedef: typedef struct { undefined6 field ; } type_undefined6_t ;
        tested on 19: 0 better, 0 worse, 0 compiling function(s) broke
   #49 [rejected] rewrite: undefined6 @1 ;  ->  uint64_t @1 = 0 ;
        tested on 8: 0 better, 0 worse

== redefinition of 'X' with a different type: 'X' (aka 'X') vs 'X' (aka 'X')
   5 idea(s), 0 adopted; parked until something changes (or run 4)
   #16 [rejected] typedef: typedef uint64_t uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #17 [no effect] rewrite: undefined1 @1 [ 16 ] ; undefined1 @2 [ 16 ] ;  ->  uint64_t @1 [ 16 ] ; uint64_t @2 [ 16 ] ;
        its 'before' text isn't in any failing line of the examples
   #18 [rejected] typedef: typedef uint64_t * undefined8 * ;
        tested on 20: 0 better, 20 worse, 2 compiling function(s) broke
   #47 [rejected] flag: -Wno-error=declaration-requires-type-id
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #48 [rejected] typedef: typedef uint64_t undefined8 ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke

== redefinition of 'X' with a different type: 'X' vs 'X' (aka 'X')
   3 idea(s), 0 adopted; parked until something changes (or run 4)
   #14 [rejected] typedef: typedef ulonglong uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #15 [rejected] typedef: typedef unsigned long long uint64_t ;
        tested on 20: 0 better, 0 worse, 0 compiling function(s) broke
   #43 [rejected] rewrite: int @1 ;  ->  uint64_t @1 ;
        tested on 10: 0 better, 0 worse

== too few arguments to function call, expected N, have N
   3 idea(s), 0 adopted; parked until something changes (or run 3)
   #20 [rejected] flag: -Wno-error=missing-argument
        tested on 18: 0 better, 0 worse, 0 compiling function(s) broke
   #21 [rejected] declare log10fWrapper: float log10fWrapper ( void ) ;
        shared.h declares no function log10fWrapper
   #22 [repeat] flag: -Wno-error=missing-argument
        same as #20

== too few arguments to function call, single argument 'X' was not specified
   3 idea(s), 0 adopted; parked until something changes (or run 3)
   #32 [rejected] declare CFRelease: void CFRelease ( void * param_1 ) ;
        shared.h declares no function CFRelease
   #33 [repeat] declare CFRelease: void CFRelease ( void * param_1 ) ;
        same as #32
   #34 [rejected] declare CFRelease: int CFRelease ( void * param_1 ) ;
        shared.h declares no function CFRelease

== too many arguments to function call, expected N, have N
   16 idea(s), 0 adopted; parked until something changes (or run 8)
   #26 [rejected] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        shared.h declares no function CFStringGetCharacters
   #27 [rejected] declare CFStringGetBytes: void CFStringGetBytes ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr ) ;
        shared.h declares no function CFStringGetBytes
   #28 [rejected] flag: -Wno-error=missing-braces
        tested on 10: 0 better, 0 worse, 0 compiling function(s) broke
   #55 [rejected] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        shared.h declares no function CFStringGetCharacters
   #56 [repeat] declare CFStringGetCharacters: void CFStringGetCharacters ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar * dstPtr
        same as #55
   #57 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #74 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #75 [rejected] declare CFStringGetBytesAndLength: void CFStringGetBytesAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar 
        shared.h declares no function CFStringGetBytesAndLength
   #76 [rejected] typedef: # define CFStringGetBytesAndLength CFStringGetBytes
        tested on 9: 0 better, 0 worse, 0 compiling function(s) broke
   #77 [repeat] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        same as #74
   #96 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
   #97 [rejected] flag: -Wno-error=extra-arg
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #98 [rejected] typedef: # define CFStringGetBytesAndLength CFStringGetBytes
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #99 [rejected] typedef: # define CFStringGetCharactersAndLength CFStringGetBytes
        tested on 8: 0 better, 0 worse, 0 compiling function(s) broke
   #116 [rejected] declare CFStringGetBytesAndLength: void CFStringGetBytesAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars , UniChar 
        shared.h declares no function CFStringGetBytesAndLength
   #117 [rejected] declare CFStringGetCharactersAndLength: void CFStringGetCharactersAndLength ( CFStringRef string , const char * srcPtr , const char * endPtr , CFIndex numChars 
        shared.h declares no function CFStringGetCharactersAndLength
```

## build/test/test_report.txt

```
Run test: the rebuilt plugin against the original (2026-10-24 19:27:58)

original: Original.component
  architectures: x86_64, arm64; tested as arm64
rebuilt:  /Users/user?/name1decomp/fastpass 3/build_c/program.dylib (arm64)

packaged the rebuilt program as /Users/user?/name1decomp/fastpass 3/build_c/test/run-ra8xyx5j/Rebuilt.component (deleted after the test), with the original's Info.plist (35 privacy stand-in(s) applied) and its Resources folder linked in

== component Illformed: Name1 (aumf/igl2/DBlu)
factory: original AUPluginFactory; rebuilt AUPluginFactory (as in the original)
rebuilt plugin, loading: FAILED
crashed (SIGSEGV) during: load executable
    CRASH signal=11 (SIGSEGV: bad memory access) address=0x0
    CRASH stack:
    0   aharness_host-arm64-325db53723      0x00000001043852a4 on_crash + 196
    1   libsystem_platform.dylib            0x000000018d081744 _sigtramp + 56
    2   program                             0x000000010a502d84 FUN_00067718 + 80
    3   program                             0x000000010a502d24 FUN_000676ec + 32
    4   program                             0x000000010a502cc4 FUN_00067690 + 56
    5   program                             0x000000010a4f7854 FUN_0005fa70 + 24
    6   program                             0x000000010a506350 FUN_0006a480 + 32
    7   program                             0x000000010a50637c FUN_0006a4c0 + 12
    8   program                             0x000000010aaab3ac gd_relocate + 1240
    9   dyld                                0x000000018ccdaa28 ___ZZNK5dyld46Loader25findAndRunAllInitializersERNS_12RuntimeStateEENK3$_0clEv_block_invoke + 180
    10  dyld                                0x000000018cce5a8c ___ZNK5dyld313MachOAnalyzer18forEachInitializerER11DiagnosticsRKNS0_15VMAddrConverterEU13block_pointerFvjEPKv_block_invoke.204 + 320
    11  dyld                                0x000000018cd25fac ___ZNK6mach_o12UnsafeHeader14forEachSectionEU13block_pointerFvRKNS0_11SectionInfoERbE_block_invoke + 312
    12  dyld                                0x000000018cd229a4 _ZNK6mach_o12UnsafeHeader18forEachLoadCommandEU13block_pointerFvPK12load_commandRbE + 208
    13  dyld                                0x000000018cd2424c _ZNK6mach_o12UnsafeHeader14forEachSectionEU13block_pointerFvRKNS0_11SectionInfoERbE + 124
    14  dyld                                0x000000018cce5580 _ZNK5dyld313MachOAnalyzer18forEachInitializerER11DiagnosticsRKNS0_15VMAddrConverterEU13block_pointerFvjEPKv + 516
    15  dyld                                0x000000018ccd5394 _ZNK5dyld46Loader25findAndRunAllInitializersERNS_12RuntimeStateE + 528
    16  dyld                                0x000000018cccdcd0 _ZNK5dyld416JustInTimeLoader15runInitializersERNS_12RuntimeStateE + 36
    17  dyld                                0x000000018ccd5ab0 _ZNK5dyld46Loader23runInitializersBottomUpERNS_12RuntimeStateERN3lsl6VectorI18AuthenticatedValueIPKS0_EEESA_ + 568
    18  dyld                                0x000000018ccdaac0 _ZZNK5dyld46Loader38runInitializersBottomUpPlusUpwardLinksERNS_12RuntimeStateEENK3$_0clEv + 116
    19  dyld                                0x000000018ccd5d98 _ZNK5dyld46Loader38runInitializersBottomUpPlusUpwardLinksERNS_12RuntimeStateE + 716
    20  dyld                                0x000000018cca42cc _ZZN5dyld44APIs11dlopen_fromEPKciPvENK3$_0clEv + 2320
    21  dyld                                0x000000018cc98004 _ZN5dyld44APIs11dlopen_fromEPKciPv + 1116
    22  dyld                                0x000000018cc97b04 _ZN5dyld44APIs6dlopenEPKci + 120
    23  CoreFoundation                      0x000000018d16c750 _CFBundleDlfcnLoadFramework + 156
    24  CoreFoundation                      0x000000018d1c2c20 _CFBundleLoadExecutableAndReturnError + 472
    25  aharness_host-arm64-325db53723      0x0000000104385628 open_unit + 204
    26  aharness_host-arm64-325db53723      0x00000001043848c8 main + 248
    27  dyld                                0x000000018ccac4e4 start + 6992
    rebuilt functions in the stack (innermost first): FUN_00067718 (funcs/_FUN_00067718.cpp), FUN_000676ec (funcs/_FUN_000676ec.cpp), FUN_00067690 (funcs/_FUN_00067690.cpp), FUN_0005fa70 (funcs/_FUN_0005fa70.cpp), FUN_0006a480 (funcs/_FUN_0006a480.cpp), FUN_0006a4c0 (funcs/_FUN_0006a4c0.cpp)
    (an address near zero: a null pointer, often a global or object the rebuilt program never set up)
    code of FUN_00067718 (funcs/_FUN_00067718.cpp):
         1 | #include "shared.h"
         2 | 
         3 | long FUN_00067718(long param_1,undefined8 param_2)
         4 | {
         5 |   undefined8 uVar1;
         6 |   undefined8 *puVar2;
         7 |   int local_34;
         8 |   undefined8 local_30;
         9 |   long lStack_28;
        10 | 
        11 |   local_30 = param_2;
        12 |   lStack_28 = param_1;
        13 |   FUN_0006777c((undefined8 *)(param_1 + 8));
        14 |   local_34 = 0;
        15 |   FUN_0006779c((long *)(param_1 + 0x10),&local_34);
        16 |   uVar1 = FUN_000677c0();
        17 |   puVar2 = (undefined8 *)FUN_000677e8();
        18 |   *puVar2 = uVar1;
        19 |   return param_1;
        20 | }
        21 | 
    code of FUN_000676ec (funcs/_FUN_000676ec.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_000676ec(long param_1,undefined8 param_2)
         4 | {
         5 |   FUN_00067718(param_1,param_2);
         6 |   return;
         7 | }
         8 | 
    code of FUN_00067690 (funcs/_FUN_00067690.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_00067690(long param_1)
         4 | {
         5 |   undefined1 auStack_30 [8];
         6 |   long local_28;
         7 | 
         8 |   local_28 = param_1;
         9 |   FUN_000676cc();
        10 |   FUN_000676ec(param_1,auStack_30);
        11 |   return;
        12 | }
        13 | 
    code of FUN_0005fa70 (funcs/_FUN_0005fa70.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0005fa70(long param_1)
         4 | {
         5 |   FUN_00067690(param_1);
         6 |   return;
         7 | }
         8 | 
    code of FUN_0006a480 (funcs/_FUN_0006a480.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006a480(void)
         4 | {
         5 |   FUN_0005fa70((uintptr_t)(g_block_29 + 0x8));
         6 |   __cxa_atexit(FUN_0005fa90,&GD_DAT_0045e138,0);
         7 |   return;
         8 | }
         9 | 
    code of FUN_0006a4c0 (funcs/_FUN_0006a4c0.cpp):
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006a4c0(void)
         4 | {
         5 |   FUN_0006a480();
         6 |   return;
         7 | }
         8 | 
    the rebuilt plugin's load steps (GD_DEBUG):
      data at 0=0x10ab7c000 1=0x10ab7da40 2=0x10af01860 3=0x10af01f20 4=0x10af24ea0 5=0x10af60330 6=0x10af7f200 7=0x10af7f340 8=0x10af81900 9=0x10af81a40 10=0x10af82490 11=0x10af9af20 12=0x10af9b880 13=0x10af9baf0 14=0x10af9bdd0 15=0x10af9bde0 16=0x10afc5c70 17=0x10afc61d0 18=0x10afc6220 19=0x10afc6240 20=0x10afc78a0 21=0x10afc83a0 22=0x10afc9950 23=0x10afca590 24=0x10afca730 25=0x10afca780 26=0x10afca810 27=0x10afca820 28=0x10afcaaf0 29=0x10afd59f0 30=0x10affed90 31=0x10b410770 32=0x10b417370 33=0x10afd78c0 34=0x10b41ada0
      fixing up 32214 pointer(s) and 1554 import(s)
      import not found (left null): dyld_stub_binder, at block 12 + 0x268
      fix-ups done; imports not found: 1
      initializer 1/91: FUN_00007144
      initializer 2/91: FUN_0000717c
      initializer 3/91: FUN_00021f34
      initializer 4/91: FUN_00035e5c
      initializer 5/91: FUN_000383cc
      initializer 6/91: FUN_0004530c
      initializer 7/91: FUN_0006a4c0
    registers when it crashed (the ones that point into the rebuilt program explained):
       x0 = 0x0000000000000000  (zero)
       x1 = 0x000000016ba7946c
       x2 = 0x00000000000120a8
       x3 = 0x000000016ba7900a
       x4 = 0x000000010aac282b  in the rebuilt program: zoom_ + 0x13d73
       x5 = 0x000000016ba79540
       x6 = 0x000000000000000a  (near zero)
       x7 = 0x0000000000000000  (zero)
       x8 = 0x0000000000000000  (zero)
       x9 = 0x0000000000000000  (zero)
      x10 = 0x0000000000000002  (near zero)
      x11 = 0x00000000fffffffd
      x12 = 0x0000000000000000  (zero)
      x13 = 0x0000000000000000  (zero)
      x14 = 0x0000000000000000  (zero)
      x15 = 0x0000000000000000  (zero)
      x16 = 0x000000018d034618
      x17 = 0x00000001fb0f7228
      x18 = 0x0000000000000000  (zero)
      x19 = 0x000000016ba79be8
      x20 = 0x000000010aaaaed4  in the rebuilt program: gd_relocate + 0x0
      x21 = 0x00000001f9801360
      x22 = 0x000000010aaaf968  in the rebuilt program: zoom_ + 0xeb0
      x23 = 0x000000010a474118
      x24 = 0x0000000000000006  (near zero)
      x25 = 0x00000000000000a0  (near zero)
      x26 = 0x000000010a474248
      x27 = 0x000000010a4740c0
      x28 = 0x0000000000000010  (near zero)
       fp = 0x000000016ba79490
       lr = 0x000000010a502d84  in the rebuilt program: FUN_00067718 + 0x50
       sp = 0x000000016ba79450
       pc = 0x000000010a502d90  in the rebuilt program: FUN_00067718 + 0x5c
    the rebuilt frames as source lines:
        2: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:17)
        3: FUN_000676ec (in program.dylib) (_FUN_000676ec.cpp:6)
        4: FUN_00067690 (in program.dylib) (_FUN_00067690.cpp:11)
        5: FUN_0005fa70 (in program.dylib) (_FUN_0005fa70.cpp:6)
        6: FUN_0006a480 (in program.dylib) (_FUN_0006a480.cpp:5)
        7: FUN_0006a4c0 (in program.dylib) (_FUN_0006a4c0.cpp:6)
        8: gd_relocate (in program.dylib) (ghidra_data.c:29976)
       pc: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:18)
       lr: FUN_00067718 (in program.dylib) (_FUN_00067718.cpp:17)
    where it crashed: FUN_00067718 line 18: *puVar2 = uVar1;
    called just before the crash: FUN_0006779c (funcs/_FUN_0006779c.cpp)
         1 | #include "shared.h"
         2 | 
         3 | void FUN_0006779c(long *param_1,int *param_2)
         4 | {
         5 |   FUN_0006786c(param_1,param_2);
         6 |   return;
         7 | }
         8 | 
    Ghidra's pseudocode of FUN_0006779c:
      void FUN_0006779c(long *param_1,int *param_2)
      
      {
        FUN_0006786c(param_1,param_2);
        return;
      }
    called just before the crash: FUN_000677c0 (funcs/_FUN_000677c0.cpp)  — Ghidra says it returns nothing; here it returns a stand-in 0
         1 | #include "shared.h"
         2 | 
         3 | uint64_t FUN_000677c0(void)
         4 | {
         5 |   FUN_000678a4();
         6 |   FUN_001fdacc();
         7 |   return 0;
         8 | }
         9 | 
    Ghidra's pseudocode of FUN_000677c0:
      void FUN_000677c0(void)
      
      {
        FUN_000678a4();
        FUN_001fdacc();
        return;
      }
    called just before the crash: FUN_000677e8 (funcs/_FUN_000677e8.cpp)  — Ghidra says it returns nothing; here it returns a stand-in 0
         1 | #include "shared.h"
         2 | 
         3 | uint64_t FUN_000677e8(void)
         4 | {
         5 |   return 0;
         6 | }
         7 | 
    Ghidra's pseudocode of FUN_000677e8:
      void FUN_000677e8(void)
      
      {
        return;
      }
    Ghidra's pseudocode of FUN_00067718:
      long FUN_00067718(long param_1,undefined8 param_2)
      
      {
        undefined8 uVar1;
        undefined8 *puVar2;
        int local_34;
        undefined8 local_30;
        long lStack_28;
        
        local_30 = param_2;
        lStack_28 = param_1;
        FUN_0006777c((undefined8 *)(param_1 + 8));
        local_34 = 0;
        FUN_0006779c((long *)(param_1 + 0x10),&local_34);
        uVar1 = FUN_000677c0();
        puVar2 = (undefined8 *)FUN_000677e8();
        *puVar2 = uVar1;
        return param_1;
      }
    Ghidra's pseudocode of FUN_000676ec:
      void FUN_000676ec(long param_1,undefined8 param_2)
      
      {
        FUN_00067718(param_1,param_2);
        return;
      }
    Ghidra's pseudocode of FUN_00067690:
      void FUN_00067690(long param_1)
      
      {
        undefined1 auStack_30 [8];
        long local_28;
        
        local_28 = param_1;
        FUN_000676cc();
        FUN_000676ec(param_1,auStack_30);
        return;
      }
    Ghidra's pseudocode of FUN_0005fa70:
      void FUN_0005fa70(long param_1)
      
      {
        FUN_00067690(param_1);
        return;
      }
    data FUN_0006a480 uses:
      GD_DAT_0045e138: block __bss + 0x8; original 0x45e138, Ghidra's DAT_0045e138; the original has there: 00 00 00 00 00 00 00 00; no fix-up there
      g_block_29 + 0x8 (an address written as a number): original 0x45e138, Ghidra's DAT_0045e138; the original has there: 00 00 00 00 00 00 00 00; no fix-up there
    Ghidra's pseudocode of FUN_0006a480:
      void FUN_0006a480(void)
      
      {
        FUN_0005fa70(0x45e138);
        ___cxa_atexit(FUN_0005fa90,&DAT_0045e138,0);
        return;
      }
    Ghidra's pseudocode of FUN_0006a4c0:
      void FUN_0006a4c0(void)
      
      {
        FUN_0006a480();
        return;
      }

the rebuilt plugin didn't load: crashed (SIGSEGV) during: load executable
```

## rewrite/data_placeholders.txt

```
Data the code names that the data export doesn't have: each gets a zero-filled
placeholder (it compiles, but reads zeros). Where it is, to see what the export misses:

DAT_800000008: not in any exported block; nearest: __LINKEDIT ends at 0x8a4000, nothing after
```

## rewrite/data_unresolved_pointers.txt

```
Pointers stored in the data that point outside every exported block: they keep
the original program's address, which doesn't exist in the rebuilt one.

at 881a73 -> 3de0
at 881aa9 -> 477c
at 881b3e -> 6b80
at 881b44 -> 6d50
at 881d44 -> f5a0
at 882040 -> 1ffbc
at 884451 -> fff8c
```

## rewrite/data_blocks.txt

```
The data export's blocks (name, start, size, writable, bytes exported):

__TEXT  0x0  6716  -  bytes
__text  0x1a3c  3685916  -  bytes
__objc_methlist  0x38a020  1724  -  bytes
__gcc_except_tab  0x38a6dc  143220  -  bytes
__const  0x3ad650  242827  -  bytes
__cstring  0x3e8adb  126659  -  bytes
__ustring  0x40799e  306  -  bytes
__objc_methname  0x407ad0  9664  -  bytes
__objc_classname  0x40a090  319  -  bytes
__objc_methtype  0x40a1cf  2629  -  bytes
__unwind_info  0x40ac14  101004  -  bytes
__eh_frame  0x4236a0  2400  -  bytes
__got  0x424000  624  w  bytes
__mod_init_func  0x424270  728  w  bytes
__DATA_CONST  0x424548  8  w  bytes
__const  0x424550  171664  -  bytes
__cfstring  0x44e3e0  1376  w  bytes
__objc_classlist  0x44e940  72  w  bytes
__objc_protolist  0x44e988  32  w  bytes
__objc_imageinfo  0x44e9a8  5720  w  bytes
__la_symbol_ptr  0x450000  2816  w  bytes
__objc_const  0x450b00  5544  w  bytes
__objc_selrefs  0x4520a8  3136  -  bytes
__objc_classrefs  0x452ce8  408  -  bytes
__objc_superrefs  0x452e80  80  -  bytes
__objc_ivar  0x452ed0  140  w  bytes
__DATA  0x452f5c  4  w  bytes
__objc_data  0x452f60  720  -  bytes
__data  0x453230  44800  w  bytes
__bss  0x45e130  7888  w  bytes
__bss  0x460000  4266456  w  zero-filled
__common  0x8719d8  27648  w  zero-filled
__DATA  0x8785d8  14888  w  zero-filled
__LINKEDIT  0x87c000  160000  -  bytes
__LINKEDIT  0x8a3100  3840  -  zero-filled
```

## rewrite/lost_returns.txt

```
Functions Ghidra says return nothing, whose callers use what they return, and that
have no call at the end whose value they could return: each returns 0 here. If the
real one returns a pointer (often what it was given), callers that use it break.

FUN_000031f4
FUN_000034cc
FUN_0000363c
FUN_000037fc
FUN_0000392c
FUN_000039f0
FUN_00003bb0
FUN_00003c94
FUN_00003d10
FUN_00004458
FUN_00004594
FUN_00004dc8
FUN_00005000
FUN_0000502c
FUN_00005070
FUN_000050fc
FUN_00005454
FUN_000058dc
FUN_00006014
FUN_000069fc
FUN_00007090
FUN_00007104
FUN_0000727c
FUN_000073b4
FUN_000073c4
FUN_000076a4
FUN_000087b8
FUN_000097a0
FUN_00009d0c
FUN_0000ab00
FUN_0000ab40
FUN_0000b780
FUN_0000b790
FUN_0000b7a0
FUN_0000b7b0
FUN_0000b7c0
FUN_0000b7d0
FUN_0000b7e0
FUN_0000b7f0
FUN_0000b800
FUN_0000b810
FUN_0000b820
FUN_0000b94c
FUN_0000bac8
FUN_0000bccc
FUN_0000bf14
FUN_0000bf44
FUN_0000c088
FUN_0000c2bc
FUN_0000c3d8
FUN_0000ccb4
FUN_0000ee7c
FUN_0000f0d0
FUN_0000f194
FUN_0000f2e8
FUN_0000f308
FUN_0000f3e8
FUN_0000fb1c
FUN_000116d0
FUN_00011f1c
FUN_00011fd4
FUN_00012150
FUN_00012280
FUN_00012bb8
FUN_00012d48
FUN_00013248
FUN_000132b0
FUN_000134f8
FUN_00013524
FUN_00014150
FUN_00015e88
FUN_00016598
FUN_00016600
FUN_00016668
FUN_000166d0
FUN_00016ba8
FUN_00016d80
FUN_00016dac
FUN_00016df0
FUN_00016e7c
FUN_000170a8
FUN_000171b4
FUN_00017f2c
FUN_00018b98
FUN_00018c38
FUN_00018dd8
FUN_0001937c
FUN_00019554
FUN_00019580
FUN_000195c4
FUN_00019650
FUN_00019b60
FUN_0001bca4
FUN_0001bd9c
FUN_0001be04
FUN_0001d354
FUN_0001dbb4
FUN_0001df78
FUN_0001e0f8
FUN_00020b58
FUN_00020e68
FUN_00021260
FUN_0002128c
FUN_00021498
FUN_00021600
FUN_0002162c
FUN_00021688
FUN_0002188c
FUN_000225fc
FUN_00023d48
FUN_00028528
FUN_000290c0
FUN_0002a188
FUN_0002af14
FUN_0002c024
FUN_0002c0b0
FUN_0002db18
FUN_0002db80
FUN_0002dc04
FUN_0002eb78
FUN_00030924
FUN_000309bc
FUN_00030a00
FUN_00030a68
FUN_00030aec
FUN_000317dc
FUN_00031824
FUN_000320fc
FUN_000322f4
FUN_0003241c
FUN_00033078
FUN_000330e0
FUN_00033510
FUN_00035030
FUN_00035098
FUN_000351d4
FUN_000358f0
FUN_00035a20
FUN_00035ce8
FUN_000367d0
FUN_000367f0
FUN_000374dc
FUN_00037834
FUN_00037fe8
FUN_000381f4
FUN_00038cf0
FUN_0003ccb4
FUN_0003cd1c
FUN_0003cd84
FUN_0003cdec
FUN_0003d7e4
FUN_0003da54
FUN_0003f81c
FUN_0003f884
FUN_0003f908
FUN_00040f04
FUN_00040f6c
FUN_00040ff0
FUN_000415c8
FUN_000415e8
FUN_00042184
FUN_000421a4
FUN_000421c4
FUN_00042a38
FUN_00043650
FUN_00044ee4
FUN_00047f24
FUN_0004a6c8
FUN_0004af6c
FUN_0004f97c
FUN_0004f9e4
FUN_00051df0
FUN_00051e58
FUN_00051edc
FUN_000520e8
FUN_000532f4
FUN_00053364
FUN_00054fd8
FUN_00055364
FUN_00056ce4
FUN_00056dd4
FUN_00057350
FUN_0005737c
FUN_000573e4
FUN_000599e4
FUN_00059a4c
FUN_00059f20
FUN_0005ac44
FUN_0005b0cc
FUN_0005b328
FUN_0005ce9c
FUN_0005cf04
FUN_0005cf88
FUN_0005eff4
FUN_0005f038
FUN_0005f0a0
FUN_0005f4f0
FUN_0005f96c
FUN_0005f994
FUN_0005fcfc
FUN_0005fd24
FUN_000613c4
FUN_00063504
FUN_000649ac
FUN_00065420
FUN_00065448
FUN_000677c0
FUN_000677e8
FUN_000679e4
FUN_00067a14
FUN_00067a88
FUN_00067ad4
FUN_00067ce4
FUN_00067dfc
FUN_0006802c
FUN_0006818c
FUN_000681d4
FUN_000682e0
FUN_00068974
FUN_00068a2c
FUN_00068b7c
FUN_00068ca4
FUN_00068cd4
FUN_00068d08
FUN_00068d4c
FUN_00069624
FUN_00069724
FUN_00069818
FUN_000698f0
FUN_00069af4
FUN_00069b38
FUN_00069fd4
FUN_0006a094
FUN_0006a1d0
FUN_0006a250
FUN_0006a280
FUN_0006a2b4
FUN_0006a514
FUN_0006a894
FUN_0006aaac
FUN_0006aad4
FUN_0006acd0
FUN_0006ad00
FUN_0006adc0
FUN_0006ae08
FUN_0006b2a4
FUN_0006b3a8
FUN_0006b3b8
FUN_0006b46c
FUN_0006b5bc
FUN_0006b64c
FUN_0006b67c
FUN_0006b6b0
FUN_0006b6f4
FUN_0006b888
FUN_0006bd68
FUN_0006c008
FUN_0006c21c
FUN_0006c244
FUN_0006c440
FUN_0006c470
FUN_0006c530
FUN_0006c578
FUN_0006ca14
FUN_0006cb18
FUN_0006cb28
FUN_0006cbdc
FUN_0006cd2c
FUN_0006cdbc
FUN_0006cdec
FUN_0006ce20
FUN_0006ce64
FUN_0006cff8
FUN_0006dca4
FUN_0006e45c
FUN_000727c4
FUN_00073024
FUN_00074b38
FUN_00075108
FUN_000768a0
FUN_00076cc8
FUN_00076f3c
FUN_00076f64
FUN_00077040
FUN_00077354
FUN_000777d0
FUN_0007798c
FUN_00077a40
FUN_00077ad4
FUN_00078744
FUN_000787e0
FUN_00078910
FUN_000789d8
FUN_00078b38
FUN_00078b80
FUN_00078c8c
FUN_0007924c
FUN_000793b0
FUN_00079474
FUN_00079770
FUN_00079a04
FUN_00079b0c
FUN_00079b34
FUN_00079b58
FUN_00079bbc
FUN_0007a008
FUN_0007a308
FUN_0007a480
FUN_0007a67c
FUN_0007aae4
FUN_0007ab38
FUN_0007b0ec
FUN_0007b10c
FUN_0007b1c0
FUN_0007b374
FUN_0007b39c
FUN_0007b65c
FUN_0007b71c
FUN_0007baa4
FUN_0007bde0
FUN_0007bee0
FUN_0007bff8
FUN_0007c50c
FUN_0007caac
FUN_0007cacc
FUN_0007cb84
FUN_0007cd3c
FUN_0007cd64
FUN_0007d024
FUN_0007d0e4
FUN_0007d470
FUN_0007d734
FUN_0007d97c
FUN_0007d9a4
FUN_0007da58
FUN_0007e000
FUN_0007e068
FUN_0007e444
FUN_0007e504
FUN_0007e88c
FUN_0007ea30
FUN_0007ebe0
FUN_0007ec64
FUN_0007f100
FUN_0007f1c0
FUN_0007f2fc
FUN_0007f37c
FUN_0007f3ac
FUN_0007f3e0
FUN_0007f810
FUN_0007fdb0
FUN_0007fdd0
FUN_0007fe84
FUN_00080038
FUN_00080060
FUN_00080320
FUN_000803e0
FUN_00080768
FUN_00080a90
FUN_00081030
FUN_00081050
FUN_00081108
FUN_000812c0
FUN_000812e8
FUN_000815a8
FUN_00081668
FUN_000819f4
FUN_00081e58
FUN_000828e0
FUN_00083394
FUN_000833b8
FUN_00084778
FUN_00085174
FUN_0008576c
FUN_00086ed0
FUN_00087154
FUN_00089f14
FUN_0008a070
FUN_0008a098
FUN_0008a1d0
FUN_0008a51c
FUN_0008a874
FUN_0008a9d4
FUN_0008aa1c
FUN_0008ab28
FUN_0008ac18
FUN_0008ad24
FUN_0008ae24
FUN_0008af18
FUN_0008b168
FUN_0008b1ac
FUN_0008b648
FUN_0008b708
FUN_0008b844
FUN_0008b8c4
FUN_0008b8f4
FUN_0008b928
FUN_0008c2a0
FUN_0008ce40
FUN_0008d2e0
FUN_0008d5e8
FUN_0008f61c
FUN_0008f684
FUN_0008febc
FUN_0009083c
FUN_00093534
FUN_0009359c
FUN_000937f4
FUN_00094eb0
FUN_00095aa4
FUN_00095acc
FUN_00095af8
FUN_00095b64
FUN_00095be4
FUN_00095f50
FUN_00096254
FUN_000962dc
FUN_00096de4
FUN_00096e58
FUN_000970e4
FUN_00098504
FUN_00098a00
FUN_00098bd0
FUN_0009a33c
FUN_0009a364
FUN_0009a38c
FUN_0009a3b4
FUN_0009c720
FUN_0009c96c
FUN_0009ca24
FUN_0009caac
FUN_0009d648
FUN_0009deac
FUN_0009def4
FUN_0009e044
FUN_0009e4e4
FUN_0009e924
FUN_0009f7e8
FUN_000a02ac
FUN_000a0acc
FUN_000a17c0
FUN_000a2150
FUN_000a3594
FUN_000a3ecc
FUN_000a5818
FUN_000a8c34
FUN_000a9758
FUN_000a97c0
FUN_000a98a8
FUN_000a9cc0
FUN_000a9ce8
FUN_000a9ee4
FUN_000a9f2c
FUN_000a9ff8
FUN_000aa040
FUN_000aa16c
FUN_000aa3c4
FUN_000aa3f0
FUN_000aa620
FUN_000aa720
FUN_000aa814
FUN_000aad14
FUN_000aadcc
FUN_000aaf14
FUN_000ab05c
FUN_000ab08c
FUN_000ab0c0
FUN_000ab41c
FUN_000ac208
FUN_000adb08
FUN_000adbc4
FUN_000aef34
FUN_000af388
FUN_000af3c8
FUN_000af544
FUN_000af614
FUN_000afa98
FUN_000afc34
FUN_000afc60
FUN_000afcc8
FUN_000b030c
FUN_000b0498
FUN_000b0770
FUN_000b0894
FUN_000b0de4
FUN_000b1b0c
FUN_000b204c
FUN_000b20b4
FUN_000b40f4
FUN_000b52f0
FUN_000b554c
FUN_000b6ee0
FUN_000b9500
FUN_000ba0c8
FUN_000ba130
FUN_000ba198
FUN_000bc7e4
FUN_000be348
FUN_000be770
FUN_000be83c
FUN_000be898
FUN_000c02c4
FUN_000c0374
FUN_000c03b4
FUN_000c0484
FUN_000c0d60
FUN_000c0f54
FUN_000c1110
FUN_000c1138
FUN_000c1160
FUN_000c1188
FUN_000c13bc
FUN_000c3754
FUN_000c37bc
FUN_000c3824
FUN_000c3de0
FUN_000c3ea8
FUN_000c3f84
FUN_000c452c
FUN_000c4554
FUN_000c4bb0
FUN_000c4fac
FUN_000c5140
FUN_000c5468
FUN_000c58a4
FUN_000c5be0
FUN_000c6a04
FUN_000c7a5c
FUN_000c7d9c
FUN_000c8108
FUN_000cb488
FUN_000ccb60
FUN_000cd188
FUN_000cd94c
FUN_000cd994
FUN_000cdb1c
FUN_000cdf84
FUN_000cef1c
FUN_000cf17c
FUN_000cf244
FUN_000cf5f0
FUN_000cf618
FUN_000d1078
FUN_000d1b18
FUN_000d2308
FUN_000d2350
FUN_000d24d8
FUN_000d2940
FUN_000d4760
FUN_000d4824
FUN_000d4b48
FUN_000d4c88
FUN_000d5310
FUN_000d5af0
FUN_000d5cf0
FUN_000da07c
FUN_000da60c
FUN_000db450
FUN_000e17e8
FUN_000e2be4
FUN_000e2c4c
FUN_000e2cf8
FUN_000e2d3c
FUN_000e4210
FUN_000e52e8
FUN_000e532c
FUN_000e6d80
FUN_000e7118
FUN_000e7784
FUN_000e7834
FUN_000e789c
FUN_000e7b30
FUN_000e7b58
FUN_000e7d54
FUN_000e7d84
FUN_000e7e3c
FUN_000e7f94
FUN_000e8094
FUN_000e81ac
FUN_000e832c
FUN_000e87d0
FUN_000e8890
FUN_000e89cc
FUN_000e8a30
FUN_000e8a60
FUN_000e8a94
FUN_000e8ad8
FUN_000e9a88
FUN_000eb60c
FUN_000ec1cc
FUN_000ec33c
FUN_000ec3a4
FUN_000ec458
FUN_000edaa0
FUN_000ef230
FUN_000ef298
FUN_000ef300
FUN_000ef368
FUN_000ef3d0
FUN_000ef438
FUN_000f05d4
FUN_000f2c64
FUN_000f2d04
FUN_000f2d80
FUN_000f2dfc
FUN_000f2e64
FUN_000f41e4
FUN_000f420c
FUN_000f4234
FUN_000f43b0
FUN_000f43d8
FUN_000f4400
FUN_000f44d8
FUN_000f46d8
FUN_000f48a0
FUN_000f695c
FUN_000f788c
FUN_000f78f4
FUN_000f795c
FUN_000f801c
FUN_000f80c8
FUN_000f89c4
FUN_000f8a08
FUN_000f8a4c
FUN_000f8abc
FUN_000ff0bc
FUN_00101b08
FUN_00101b84
FUN_00101ccc
FUN_00101df8
FUN_00101ec8
FUN_00101f9c
FUN_00102098
FUN_00102184
FUN_00109d94
FUN_0010a408
FUN_0010a4b0
FUN_0010a634
FUN_0010dfd0
FUN_0010e070
FUN_00111de8
FUN_00111e74
FUN_001120e4
FUN_00112514
FUN_00112680
FUN_00113bd0
FUN_0011437c
FUN_00114b0c
FUN_00115e28
FUN_00117e80
FUN_00118484
FUN_00119d9c
FUN_00119de4
FUN_00119fa4
FUN_0011a6d4
FUN_0011aaec
FUN_0011ad10
FUN_0011ad24
FUN_0011b0ac
FUN_0011b114
FUN_0011b33c
FUN_0011b3b0
FUN_0011ba10
FUN_0011ba8c
FUN_0011c2e0
FUN_0011c4d0
FUN_0011c928
FUN_0011c968
FUN_0011d018
FUN_0011d154
FUN_0011d17c
FUN_0011d550
FUN_0011d770
FUN_0011dd38
FUN_0011e170
FUN_0011e1f8
FUN_0011e690
FUN_0011fcdc
FUN_001201fc
FUN_00121868
FUN_0012474c
FUN_001247b4
FUN_0012481c
FUN_00124b18
FUN_00125478
FUN_00126010
FUN_00126118
FUN_001262e8
FUN_00126390
FUN_001264c4
FUN_00126684
FUN_0012673c
FUN_00126854
FUN_00126904
FUN_00126a34
FUN_00126fd8
FUN_001276f4
FUN_00127850
FUN_00128014
FUN_00128200
FUN_001282ac
FUN_00129080
FUN_001296c8
FUN_001297c0
FUN_001298dc
FUN_0012a1d4
FUN_0012a698
FUN_0012a6d8
FUN_0012b6fc
FUN_0012b764
FUN_0012bb84
FUN_0012bbec
FUN_0012bd48
FUN_0012be38
FUN_0012bf08
FUN_0012bf84
FUN_0012c078
FUN_0012c098
FUN_0012c644
FUN_0012c668
FUN_0012c70c
FUN_0012c750
FUN_0012c8bc
FUN_0012c948
FUN_0012c978
FUN_0012c9ac
FUN_0012c9bc
FUN_0012ca00
FUN_0012cd58
FUN_0012db5c
FUN_0012e2d4
FUN_0012e8d4
FUN_0012eda8
FUN_0012ee0c
FUN_0012f044
FUN_0012f304
FUN_0012f4c4
FUN_001304dc
FUN_00131888
FUN_001318f0
FUN_00131958
FUN_00131ae0
FUN_00131d50
FUN_00131ff4
FUN_00132798
FUN_0013696c
FUN_001377ac
FUN_0013785c
FUN_00137a54
FUN_00137c98
FUN_00138038
FUN_0013805c
FUN_00138084
FUN_0013838c
FUN_001383b4
FUN_001385d8
FUN_00138620
FUN_0013872c
FUN_00138e24
FUN_00139018
FUN_00139118
FUN_0013920c
FUN_001394d0
FUN_001395f4
FUN_0013970c
FUN_0013972c
FUN_00139aec
FUN_00139b34
FUN_00139c30
FUN_0013a0cc
FUN_0013a18c
FUN_0013a2c4
FUN_0013a344
FUN_0013a374
FUN_0013a3a8
FUN_0013a3ec
FUN_0013a5b4
FUN_0013aa58
FUN_0013ab18
FUN_0013ac54
FUN_0013ad0c
FUN_0013ad3c
FUN_0013ad70
FUN_0013af84
FUN_0013b090
FUN_0013b5c8
FUN_0013b62c
FUN_0013b814
FUN_0013ceb4
FUN_0013e1b8
FUN_0013e1e0
FUN_0013e2a8
FUN_0013e2dc
FUN_0013e304
FUN_0013e414
FUN_0013e524
FUN_0013e57c
FUN_0013e654
FUN_0013e808
FUN_0013e86c
FUN_0013ebe8
FUN_0013ed68
FUN_0013f1b4
FUN_0013f2cc
FUN_0013f330
FUN_0013f354
FUN_0013f61c
FUN_0013f650
FUN_0013f894
FUN_0013f8ec
FUN_0013f924
FUN_0013fc90
FUN_001401dc
FUN_00140efc
FUN_00140ff4
FUN_001411d0
FUN_00141550
FUN_00141658
FUN_0014167c
FUN_00141f20
FUN_00142054
FUN_00142068
FUN_0014207c
FUN_0014211c
FUN_001425a4
FUN_0014274c
FUN_00142798
FUN_001427dc
FUN_00142d70
FUN_00142f78
FUN_00143304
FUN_00143e94
FUN_00144010
FUN_001440cc
FUN_001440f4
FUN_0014429c
FUN_00144490
FUN_001445e0
FUN_00144654
FUN_00144bf8
FUN_00145ae0
FUN_00145c6c
FUN_00146614
FUN_0014cce0
FUN_0014d03c
FUN_0014e820
FUN_0014ec20
FUN_0014ecf8
FUN_0014f024
FUN_0014f4b8
FUN_0014f4d8
FUN_0014f79c
FUN_0014f7fc
FUN_0014fd40
FUN_00150e78
FUN_00150e9c
FUN_00150ecc
FUN_00151024
FUN_00151130
FUN_001516bc
FUN_00151b28
FUN_00151bd8
FUN_00151d10
FUN_00151e10
FUN_00152018
FUN_00152154
FUN_001521e0
FUN_00152370
FUN_00152384
FUN_00152398
FUN_001523d4
FUN_00152f00
FUN_00153020
FUN_0015304c
FUN_001534e0
FUN_00153574
FUN_001536dc
FUN_00153a10
FUN_00153a44
FUN_00153b00
FUN_00153b14
FUN_00153b28
FUN_00153b64
FUN_00154328
FUN_00154694
FUN_0015480c
FUN_001549f0
FUN_00155c30
FUN_00155e84
FUN_00156a08
FUN_00156c84
FUN_00156dd0
FUN_00156e38
FUN_0015743c
FUN_001574a4
FUN_00157b54
FUN_00157bac
FUN_00157c7c
FUN_0015840c
FUN_00158d80
FUN_001593ec
FUN_00159c10
FUN_00159c58
FUN_00159de0
FUN_0015a248
FUN_0015b25c
FUN_0016342c
FUN_0016374c
FUN_00164c48
FUN_00164d7c
FUN_00164dc4
FUN_00164f38
FUN_00164f60
FUN_0016516c
FUN_00165194
FUN_00165390
FUN_001653d8
FUN_001654a0
FUN_001654ec
FUN_00165654
FUN_0016569c
FUN_00165750
FUN_0016579c
FUN_0016584c
FUN_001658f8
FUN_00165dac
FUN_00165eb0
FUN_00165ec0
FUN_00165f78
FUN_001660d0
FUN_001661fc
FUN_0016622c
FUN_00166260
FUN_001668b4
FUN_001669c4
FUN_001669d4
FUN_00166a8c
FUN_00166be4
FUN_00166cd8
FUN_00166d08
FUN_00166d3c
FUN_00167084
FUN_0016737c
FUN_00168248
FUN_0016836c
FUN_0016ce28
FUN_0016d174
FUN_0016d4a8
FUN_0016dd48
FUN_0016e4b8
FUN_0016e54c
FUN_0016e5e0
FUN_0016e6b4
FUN_0016e990
FUN_0016e9e0
FUN_0016ef98
FUN_0016efb8
FUN_0016f06c
FUN_0016f220
FUN_0016f248
FUN_0016f508
FUN_0016f5c8
FUN_0016f95c
FUN_0017033c
FUN_0017036c
FUN_001709c8
FUN_00171bb8
FUN_00171f84
FUN_00172890
FUN_001739d0
FUN_001739f8
FUN_00173bf4
FUN_00173c3c
FUN_00173da0
FUN_00173e1c
FUN_00173eb0
FUN_001751cc
FUN_00175758
FUN_00175864
FUN_00176728
FUN_0017676c
FUN_00177170
FUN_001771c4
FUN_00177a60
FUN_00178584
FUN_001788bc
FUN_001799f4
FUN_0017a2d8
FUN_0017aee0
FUN_0017af08
FUN_0017c930
FUN_0017c940
FUN_0017cde0
FUN_0017ce08
FUN_0017d968
FUN_0017d990
FUN_0017da88
FUN_0017dab0
FUN_0017ec70
FUN_0017fa38
FUN_0017fb58
FUN_00180648
FUN_001814a0
FUN_001841a4
FUN_001841d4
FUN_00184200
FUN_00184c14
FUN_00184c44
FUN_00184c70
FUN_001852b0
FUN_001852e0
FUN_0018530c
FUN_00185d40
FUN_00185d70
FUN_00185d9c
FUN_00186b78
FUN_00186ba8
FUN_00186bd4
FUN_00187928
FUN_00187958
FUN_00187984
FUN_00188058
FUN_0018cb78
FUN_0018cba8
FUN_0018cbd4
FUN_0018d568
FUN_0018d598
FUN_0018d5c4
FUN_0018dc04
FUN_0018dc34
FUN_0018dc60
FUN_0018e664
FUN_0018e694
FUN_0018e6c0
FUN_0018f404
FUN_0018f434
FUN_0018f460
FUN_001901b4
FUN_001901e4
FUN_00190210
FUN_001908e4
FUN_001954b8
FUN_001954e8
FUN_00195514
FUN_00195eb4
FUN_00195ee4
FUN_00195f10
FUN_00196550
FUN_00196580
FUN_001965ac
FUN_00196fb0
FUN_00196fe0
FUN_0019700c
FUN_00197d4c
FUN_00197d7c
FUN_00197da8
FUN_00198af4
FUN_00198b24
FUN_00198b50
FUN_00199220
FUN_0019ded0
FUN_0019df00
FUN_0019df2c
FUN_0019e8c0
FUN_0019e8f0
FUN_0019e91c
FUN_0019ef5c
FUN_0019ef8c
FUN_0019efb8
FUN_0019f9bc
FUN_0019f9ec
FUN_0019fa18
FUN_001a074c
FUN_001a077c
FUN_001a07a8
FUN_001a14e8
FUN_001a1518
FUN_001a1544
FUN_001a2440
FUN_001a29c0
FUN_001a305c
FUN_001a30e4
FUN_001a314c
FUN_001a6458
FUN_001a6724
FUN_001a6830
FUN_001a6858
FUN_001a687c
FUN_001a68c8
FUN_001a68ec
FUN_001a6abc
FUN_001a6ae0
FUN_001a70dc
FUN_001a72a8
FUN_001a7360
FUN_001a7478
FUN_001a7508
FUN_001a7ac8
FUN_001a7af0
FUN_001a7b14
FUN_001a7fc8
FUN_001a83a0
FUN_001a8f80
FUN_001a9578
FUN_001a9718
FUN_001a9b98
FUN_001aa24c
FUN_001aa674
FUN_001aa844
FUN_001aadd0
FUN_001aadf8
FUN_001aaff4
FUN_001ab024
FUN_001ab098
FUN_001ab0e4
FUN_001ab2f4
FUN_001ab40c
FUN_001ab910
FUN_001ab9c8
FUN_001abb18
FUN_001abc44
FUN_001abc74
FUN_001abca8
FUN_001abcec
FUN_001ac920
FUN_001acb74
FUN_001acc68
FUN_001ae170
FUN_001ae1f4
FUN_001ae6c8
FUN_001ae7d4
FUN_001ae8d4
FUN_001ae9c8
FUN_001aec04
FUN_001af0a0
FUN_001af160
FUN_001af298
FUN_001af338
FUN_001af368
FUN_001af39c
FUN_001af5dc
FUN_001af62c
FUN_001af9e4
FUN_001aff18
FUN_001b4544
FUN_001b4708
FUN_001b4c98
FUN_001b708c
FUN_001b70d0
FUN_001b7894
FUN_001b7ba8
FUN_001b9308
FUN_001b934c
FUN_001b9390
FUN_001b93d4
FUN_001b9564
FUN_001b958c
FUN_001b9700
FUN_001b9904
FUN_001b9a64
FUN_001b9aac
FUN_001b9bb8
FUN_001b9c68
FUN_001b9d74
FUN_001b9e74
FUN_001b9f9c
FUN_001ba11c
FUN_001ba36c
FUN_001ba7e8
FUN_001ba8a8
FUN_001ba9e4
FUN_001baa64
FUN_001baa94
FUN_001baac8
FUN_001bae1c
FUN_001bb008
FUN_001bb79c
FUN_001bbe6c
FUN_001bc614
FUN_001bc914
FUN_001bcd38
FUN_001bd140
FUN_001bd1b8
FUN_001bd358
FUN_001bd778
FUN_001bd7a0
FUN_001be424
FUN_001be7ac
FUN_001be978
FUN_001bea30
FUN_001beb48
FUN_001beccc
FUN_001becf4
FUN_001beef0
FUN_001bef20
FUN_001bef94
FUN_001befe0
FUN_001bf20c
FUN_001bf300
FUN_001bf818
FUN_001bf8d0
FUN_001bfa20
FUN_001bfb18
FUN_001bfb48
FUN_001bfb7c
FUN_001bfbc0
FUN_001bffa4
FUN_001c0564
FUN_001c058c
FUN_001c05b0
FUN_001c0a64
FUN_001c0e3c
FUN_001c16a0
FUN_001c1b84
FUN_001c1dd8
FUN_001c1e00
FUN_001c1f98
FUN_001c2150
FUN_001c2924
FUN_001c2e28
FUN_001c2fb8
FUN_001c3140
FUN_001c31a8
FUN_001c391c
FUN_001c542c
FUN_001c5654
FUN_001c57c4
FUN_001c6ee4
FUN_001c6f4c
FUN_001c7904
FUN_001c8efc
FUN_001c94b4
FUN_001c9534
FUN_001c955c
FUN_001c989c
FUN_001c991c
FUN_001c9a98
FUN_001c9d6c
FUN_001c9eec
FUN_001ca018
FUN_001ca04c
FUN_001ca074
FUN_001ca2a4
FUN_001cb9bc
FUN_001cbaf0
FUN_001cbba0
FUN_001cc2d8
FUN_001cc2e8
FUN_001cc310
FUN_001ccf0c
FUN_001cd26c
FUN_001cd294
FUN_001cd488
FUN_001cd4ac
FUN_001cd4f4
FUN_001cd604
FUN_001cd66c
FUN_001cd7d0
FUN_001cd8d0
FUN_001cd9f4
FUN_001cdb74
FUN_001ce010
FUN_001ce0d0
FUN_001ce208
FUN_001ce2a8
FUN_001ce2d8
FUN_001ce30c
FUN_001cf97c
FUN_001d1544
FUN_001d1850
FUN_001d1860
FUN_001d1870
FUN_001d18b4
FUN_001d18dc
FUN_001d43ac
FUN_001d43d4
FUN_001d454c
FUN_001d47b0
FUN_001d4b54
FUN_001d4cb4
FUN_001d4cfc
FUN_001d4e08
FUN_001d4eb8
FUN_001d4f34
FUN_001d5040
FUN_001d5140
FUN_001d5234
FUN_001d5450
FUN_001d58ec
FUN_001d59ac
FUN_001d5ae8
FUN_001d5ba0
FUN_001d5bd0
FUN_001d5c04
FUN_001d627c
FUN_001d69f4
FUN_001d6b24
FUN_001d6ea8
FUN_001d6ed0
FUN_001d6fb8
FUN_001d70f8
FUN_001d7140
FUN_001d72a4
FUN_001d73b4
FUN_001d74b4
FUN_001d75a8
FUN_001d7728
FUN_001d7bc4
FUN_001d7c84
FUN_001d7dbc
FUN_001d7eb0
FUN_001d7ee0
FUN_001d7f14
FUN_001d7f58
FUN_001d94f4
FUN_001d9700
FUN_001d9728
FUN_001d9810
FUN_001d9950
FUN_001d9998
FUN_001d9a90
FUN_001d9ba0
FUN_001d9ca0
FUN_001d9d94
FUN_001d9e24
FUN_001da2c0
FUN_001da380
FUN_001da4bc
FUN_001da530
FUN_001da560
FUN_001da594
FUN_001da5d8
FUN_001da8a8
FUN_001da8c8
FUN_001db2fc
FUN_001dbb54
FUN_001dbb9c
FUN_001dc59c
FUN_001dc730
FUN_001dc75c
FUN_001de8f4
FUN_001deb2c
FUN_001dec80
FUN_001dedc0
FUN_001df098
FUN_001e0524
FUN_001e058c
FUN_001e0b8c
FUN_001e0ec8
FUN_001e0ed8
FUN_001e12b4
FUN_001e1b3c
FUN_001e1ccc
FUN_001e1cf4
FUN_001e1e78
FUN_001e20f4
FUN_001e2118
FUN_001e2148
FUN_001e21f0
FUN_001e2258
FUN_001e2468
FUN_001e253c
FUN_001e271c
FUN_001e2760
FUN_001e2bcc
FUN_001e2c8c
FUN_001e2dc8
FUN_001e2e2c
FUN_001e2e5c
FUN_001e2e90
FUN_001e30e0
FUN_001e34c0
FUN_001e34ec
FUN_001e37c0
FUN_001e3a74
FUN_001e3a9c
FUN_001e3c90
FUN_001e3cb4
FUN_001e3cfc
FUN_001e3e08
FUN_001e3e70
FUN_001e3fd4
FUN_001e40d4
FUN_001e41ec
FUN_001e436c
FUN_001e4808
FUN_001e48c8
FUN_001e4a04
FUN_001e4a84
FUN_001e4ab4
FUN_001e4ae8
FUN_001e5258
FUN_001e740c
FUN_001e74ac
FUN_001e77fc
FUN_001e793c
FUN_001e7984
FUN_001e7a7c
FUN_001e7bf0
FUN_001e7c18
FUN_001e7cd4
FUN_001e8170
FUN_001e8250
FUN_001e8260
FUN_001e8320
FUN_001e845c
FUN_001e84d0
FUN_001e8500
FUN_001e8534
FUN_001e8578
FUN_001e870c
FUN_001eb890
FUN_001ec6a4
FUN_001eca74
FUN_001ed16c
FUN_001ed300
FUN_001ed3b4
FUN_001ee2ac
FUN_001f07b4
FUN_001f1444
FUN_001f1488
FUN_001f14cc
FUN_001f1510
FUN_001f1ab4
FUN_001f1d5c
FUN_001f1d80
FUN_001f1dbc
FUN_001f4cb4
FUN_001f4ff4
FUN_001f529c
FUN_001f5464
FUN_001f54e4
FUN_001f6d2c
FUN_001f6dd4
FUN_001f7550
FUN_001f7594
FUN_001f75d8
FUN_001f7668
FUN_001f7ec4
FUN_001f7f0c
FUN_001f8700
FUN_001f8720
FUN_001f88dc
FUN_001f8f20
FUN_001f934c
FUN_001f9a0c
FUN_001f9b30
FUN_001f9bc4
FUN_001f9c68
FUN_001f9ca8
FUN_001f9d50
FUN_001f9dec
FUN_001f9e9c
FUN_001fac70
FUN_001fda2c
FUN_001fda54
FUN_001fdc44
FUN_001fdc8c
FUN_001fde04
FUN_001fdf24
FUN_001fe024
FUN_001fe144
FUN_001fe21c
FUN_001fe6b8
FUN_001fe76c
FUN_001fe91c
FUN_001fe9e8
FUN_001fea18
FUN_001febc4
FUN_001fed54
FUN_001ff2d4
FUN_001ff5b4
FUN_001ff638
FUN_00200b48
FUN_00201aac
FUN_002023cc
FUN_0020275c
FUN_00202914
FUN_00202ae0
FUN_00202b7c
FUN_00202c94
FUN_00202d90
FUN_00202f5c
FUN_00202ff8
FUN_00203110
FUN_002032ac
FUN_0020386c
FUN_00203894
FUN_002038b8
FUN_00203bc4
FUN_00203eec
FUN_0020408c
FUN_002040d0
FUN_00204690
FUN_002046b8
FUN_002046dc
FUN_002049e8
FUN_00204d10
FUN_00204eb0
FUN_00204fa4
FUN_00205150
FUN_002051ec
FUN_0020531c
FUN_00205370
FUN_002059b4
FUN_002059dc
FUN_00205a00
FUN_00205d40
FUN_00205fac
FUN_00206094
FUN_00206234
FUN_002063b8
FUN_00206aa0
FUN_00208454
FUN_002089d4
FUN_00208bd4
FUN_00208d54
FUN_00208d74
FUN_00209648
FUN_00209754
FUN_0020a0e0
FUN_0020a1ec
FUN_0020b28c
FUN_0020d198
FUN_0020e018
FUN_0020e0d4
FUN_0020e17c
FUN_0020e24c
FUN_0020e2c8
FUN_0020e3d8
FUN_0020e3fc
FUN_0020e40c
FUN_0020eaec
FUN_0020ebb0
FUN_0020ec10
FUN_0020ee54
FUN_0020ee64
FUN_0020ee78
FUN_0020ef28
FUN_0020f3c0
FUN_0020f3e8
FUN_0020f8cc
FUN_0020f91c
FUN_0020f98c
FUN_00210064
FUN_00210120
FUN_002110a4
FUN_00211664
FUN_0021168c
FUN_002116b0
FUN_00211b64
FUN_00211f3c
FUN_00211f80
FUN_0021255c
FUN_00212584
FUN_002125a8
FUN_002128d4
FUN_00212b14
FUN_00212bfc
FUN_00212da8
FUN_00213588
FUN_00213ec8
FUN_00213fe4
FUN_00215b64
FUN_00215ca4
FUN_002165c8
FUN_00216b34
FUN_00216b48
FUN_00216ca4
FUN_00216d38
FUN_00216d74
FUN_00217130
FUN_00217338
FUN_00217460
FUN_00217470
FUN_00217b00
FUN_00217f74
FUN_0021859c
FUN_0021876c
FUN_00218918
FUN_002189b4
FUN_00218acc
FUN_00218df8
FUN_00218e20
FUN_00218e44
FUN_0021900c
FUN_0021932c
FUN_00219724
FUN_00219784
FUN_0021980c
FUN_00219a3c
FUN_00219d64
FUN_00219da4
FUN_00219ffc
FUN_0021a214
FUN_0021a254
FUN_0021ae4c
FUN_0021aec0
FUN_0021af20
FUN_0021b59c
FUN_0021b7f4
FUN_0021d924
FUN_0021eb34
FUN_00223210
FUN_00223664
FUN_00223688
FUN_00223808
FUN_00223a9c
FUN_00223aec
FUN_00223b5c
FUN_00225cec
FUN_00225e28
FUN_00225e4c
FUN_00225ea0
FUN_00225ec4
FUN_00226248
FUN_00226284
FUN_002263c4
FUN_002263e8
FUN_0022643c
FUN_00226460
FUN_00226714
FUN_00226750
FUN_002267b4
FUN_002268f0
FUN_00226910
FUN_002269c8
FUN_00226b5c
FUN_00226ba0
FUN_00226bd0
FUN_00226bf4
FUN_00226c54
FUN_00226d14
FUN_00226e44
FUN_00227308
FUN_00227344
FUN_00227440
FUN_002274fc
FUN_00227638
FUN_00227658
FUN_00227710
FUN_0022789c
FUN_002278f0
FUN_00227920
FUN_00227944
FUN_002279a4
FUN_00227a64
FUN_00227bf8
FUN_00227d04
FUN_00227ea8
FUN_00227f38
FUN_00228854
FUN_002288fc
FUN_00228da4
FUN_002293a4
FUN_002297e4
FUN_0022ac20
FUN_0022b1ac
FUN_0022b3e8
FUN_0022b510
FUN_0022b66c
FUN_0022bd58
FUN_0022bd7c
FUN_0022bda4
FUN_0022bf54
FUN_0022bf7c
FUN_0022c158
FUN_0022c1a0
FUN_0022c2ac
FUN_0022c3bc
FUN_0022c4bc
FUN_0022c5d4
FUN_0022c6dc
FUN_0022c954
FUN_0022cc48
FUN_0022cc78
FUN_0022cd10
FUN_0022cd58
FUN_0022d1dc
FUN_0022d29c
FUN_0022d3d4
FUN_0022d454
FUN_0022d484
FUN_0022d4b8
FUN_0022d764
FUN_0022daac
FUN_0022db24
FUN_0022dbd4
FUN_0022dd10
FUN_0022dd38
FUN_0022dd68
FUN_0022dd9c
FUN_0022e2c4
FUN_0022e850
FUN_0022e930
FUN_002307dc
FUN_002307f0
FUN_00230cc0
FUN_00231534
FUN_00231560
FUN_00234824
FUN_002348f8
FUN_00234d38
FUN_00235224
FUN_00235ee4
FUN_0023ba78
FUN_0023bcc0
FUN_0024310c
FUN_00243204
FUN_00244830
FUN_002477c4
FUN_00247fbc
FUN_00248034
FUN_002494b4
FUN_0024a2bc
FUN_0024aa4c
FUN_0024aa6c
FUN_0024ac00
FUN_0024fbec
FUN_00250a70
FUN_0025116c
FUN_0025118c
FUN_0025244c
FUN_0025275c
FUN_00252874
FUN_00253104
FUN_00254ae0
FUN_00254bc8
FUN_00255170
FUN_0025519c
FUN_00255514
FUN_0025cc34
FUN_00261d40
FUN_00263604
FUN_00265274
FUN_00266a74
FUN_00266ca4
FUN_0026710c
FUN_002682a0
FUN_0026834c
FUN_00268810
FUN_0026909c
FUN_00269edc
FUN_00269ef8
FUN_00269f6c
FUN_00269f8c
FUN_00269fd0
FUN_0026a018
FUN_0026a0b4
FUN_0026a0f8
FUN_0026a150
FUN_0026a228
FUN_0026a284
FUN_0026a3d0
FUN_0026a810
FUN_0026a824
FUN_0026aa80
FUN_0026ab60
FUN_0026ad24
FUN_0026add8
FUN_0026b100
FUN_0026b11c
FUN_0026b16c
FUN_0026b188
FUN_0026b1b0
FUN_0026b328
FUN_0026b340
FUN_0026b458
FUN_0026b4a4
FUN_0026b7e0
FUN_0026b7f4
FUN_0026b854
FUN_0026b958
FUN_0026b970
FUN_0026ba48
FUN_0026c234
FUN_0026c408
FUN_0026c46c
FUN_0026d100
FUN_0026e0dc
FUN_0026fc10
FUN_0026ff3c
FUN_00270228
FUN_00270d2c
FUN_00270d48
FUN_00270f10
FUN_00270fbc
FUN_00271040
FUN_002710e8
FUN_002711a4
FUN_00271200
FUN_00271308
FUN_00271364
FUN_002714fc
FUN_00271510
FUN_0027170c
FUN_00271724
FUN_002717fc
FUN_002719b4
FUN_002719c8
FUN_00271b34
FUN_00271b4c
FUN_00271c40
FUN_00272014
FUN_002721a8
FUN_00272304
FUN_00272fa4
FUN_0027302c
FUN_0027320c
FUN_002732a0
FUN_00273390
FUN_002739cc
FUN_002739ec
FUN_002795a0
FUN_0027995c
FUN_0027c758
FUN_0027c780
FUN_0027f4a0
FUN_0027f524
FUN_002807ac
FUN_00280990
FUN_00280a84
FUN_00280ba0
FUN_00280bbc
FUN_00280ea8
FUN_00280f0c
FUN_00280f60
FUN_00281014
FUN_00281100
FUN_0028112c
FUN_002811cc
FUN_002812b8
FUN_0028131c
FUN_002816f8
FUN_00281710
FUN_002817b4
FUN_00281890
FUN_00281978
FUN_002819c8
FUN_002819e4
FUN_00281a00
FUN_00281b94
FUN_00281bac
FUN_00281cc4
FUN_00281cf4
FUN_0028206c
FUN_00282084
FUN_00282124
FUN_00282128
FUN_00282178
FUN_00282194
FUN_002821b0
FUN_00282328
FUN_00282340
FUN_00282458
FUN_00282484
FUN_00282670
FUN_00282afc
FUN_00282c5c
FUN_00284a84
FUN_00285274
FUN_00285330
FUN_00285690
FUN_00285ea8
FUN_0028619c
FUN_002861b8
FUN_0028637c
FUN_002863dc
FUN_00286424
FUN_00286458
FUN_0028671c
FUN_00286734
FUN_002867d8
FUN_002867dc
FUN_0028682c
FUN_00286848
FUN_00286864
FUN_002869f0
FUN_00286a08
FUN_00286b20
FUN_00286b6c
FUN_0028ad14
FUN_0028ad60
FUN_0028d718
FUN_0028d774
FUN_0028d7f0
FUN_0028de40
FUN_0028de48
FUN_0028dfd0
FUN_0028e234
FUN_0028e300
FUN_0028e314
FUN_0028e47c
FUN_0028e590
FUN_0028e6a0
FUN_0028e6b8
FUN_0028ec7c
FUN_0028fb48
FUN_002909a0
FUN_002909a8
FUN_00290b30
FUN_00290ddc
FUN_00290ed0
FUN_00290ee4
FUN_002910dc
FUN_002911f8
FUN_00293328
FUN_002945bc
FUN_00299fa0
FUN_0029a020
FUN_0029a1d8
FUN_0029a1f0
FUN_0029a204
FUN_0029a234
FUN_0029e648
FUN_0029f780
FUN_0029f794
FUN_0029f894
FUN_0029f8e8
FUN_0029f988
FUN_0029f9a0
FUN_0029faf0
FUN_0029fb0c
FUN_0029ff2c
FUN_0029ff48
FUN_0029ff60
FUN_0029ffd8
FUN_002a0038
FUN_002a0114
FUN_002a012c
FUN_002a017c
FUN_002a0198
FUN_002a01b4
FUN_002a034c
FUN_002a0364
FUN_002a047c
FUN_002a04ac
FUN_002a06ac
FUN_002a0a28
FUN_002a0a44
FUN_002a0b5c
FUN_002a0b78
FUN_002a0da0
FUN_002a0e54
FUN_002a0e60
FUN_002a1188
FUN_002a118c
FUN_002a11a4
FUN_002a11bc
FUN_002a120c
FUN_002a1228
FUN_002a1250
FUN_002a13e0
FUN_002a13f8
FUN_002a1510
FUN_002a153c
FUN_002a18e8
FUN_002a1904
FUN_002a191c
FUN_002a1990
FUN_002a19d8
FUN_002a19dc
FUN_002a19f4
FUN_002a1a5c
FUN_002a1a7c
FUN_002a1c0c
FUN_002a1c24
FUN_002a1d3c
FUN_002a1d68
FUN_002a1ef0
FUN_002a22a4
FUN_002a4f34
FUN_002aabb4
FUN_002aabdc
FUN_002ab534
FUN_002b2404
FUN_002b2c18
FUN_002b52fc
FUN_002c2950
FUN_002c2980
FUN_002c3794
FUN_002c381c
FUN_002c4bc4
FUN_002cb60c
FUN_002cba20
FUN_002cbec4
FUN_002cc6e0
FUN_002ce4d4
FUN_002ce550
FUN_002d2278
FUN_002d4b48
FUN_002d5510
FUN_002d5604
FUN_002d57a0
FUN_002e9a6c
FUN_002eab84
FUN_002eabd4
FUN_002eac7c
FUN_002ef838
FUN_002f0974
FUN_002f0af4
FUN_002f1024
FUN_002f19e4
FUN_002f1d78
FUN_002f1eb8
FUN_002f1fd0
FUN_002f2628
FUN_002f27a8
FUN_002f2974
FUN_002f3b2c
FUN_002f3c2c
FUN_002f3df8
FUN_002f3e9c
FUN_002f4068
FUN_002f423c
FUN_002f425c
FUN_002f4320
FUN_002f4364
FUN_002f4894
FUN_002f48bc
FUN_002f5a94
FUN_002f712c
FUN_002f934c
FUN_002fb2a4
FUN_002fb554
FUN_002fcf24
FUN_002fd4f4
FUN_0030014c
FUN_003004ac
FUN_00300f78
FUN_00301068
FUN_003021b0
FUN_0030ab8c
FUN_0030e608
FUN_0030e61c
FUN_0030f060
FUN_0030f444
FUN_003149a4
FUN_00314bb4
FUN_00315318
FUN_0031b148
FUN_0031b640
FUN_0031be70
FUN_0031c530
FUN_0031eb0c
FUN_0031ebf0
FUN_0031ec70
FUN_0031ecd0
FUN_0031ee28
FUN_0031eed4
FUN_0031ef54
FUN_0031ef8c
FUN_0031f0e4
FUN_0031f190
FUN_0031f210
FUN_0031f248
FUN_0031f32c
FUN_0031f348
FUN_0031f418
FUN_0031f494
FUN_0031f500
FUN_0031f630
FUN_0031f6d4
FUN_0031f73c
FUN_0031f8e4
FUN_0031f94c
FUN_0031fa7c
FUN_0031fc98
FUN_0031fd4c
FUN_0031fd58
FUN_00320048
FUN_0032004c
FUN_00320068
FUN_00320080
FUN_003200d0
FUN_003200ec
FUN_00320108
FUN_00320338
FUN_00320350
FUN_00320468
FUN_00320494
FUN_00320870
FUN_00320af0
FUN_003210d0
FUN_003210e8
FUN_00321280
FUN_003212a8
FUN_0032153c
FUN_00321728
FUN_00321740
FUN_00321758
FUN_003217e8
FUN_003218e4
FUN_00321be4
FUN_00321e64
FUN_00322430
FUN_00322448
FUN_003225e0
FUN_00322608
FUN_0032285c
FUN_00322a48
FUN_00322a60
FUN_00322a78
FUN_00322b08
FUN_00322c04
FUN_00322f04
FUN_00323184
FUN_00323750
FUN_00323768
FUN_00323900
FUN_00323928
FUN_00323b7c
FUN_00323d68
FUN_00323d80
FUN_00323d98
FUN_00323e28
FUN_00323f24
FUN_00325488
FUN_00325a14
FUN_00325a54
FUN_00325b14
FUN_00325bec
FUN_00325d90
FUN_00325dec
FUN_00326000
FUN_00326028
FUN_0032648c
FUN_00326800
FUN_00326aec
FUN_00326bf0
FUN_00326c0c
FUN_00326dd0
FUN_00326e30
FUN_00326e78
FUN_00327140
FUN_00327158
FUN_003271fc
FUN_00327200
FUN_00327250
FUN_0032726c
FUN_00327288
FUN_00327414
FUN_0032742c
FUN_00327544
FUN_00327590
FUN_003276d8
FUN_003276f4
FUN_003279ec
FUN_00327a08
FUN_00327a20
FUN_00327a94
FUN_00327af0
FUN_00327af4
FUN_00327b0c
FUN_00327b5c
FUN_00327b78
FUN_00327b94
FUN_00327d20
FUN_00327d38
FUN_00327e50
FUN_00327e7c
FUN_0032a038
FUN_0032ba84
FUN_0032c6a4
FUN_0032dc78
FUN_00330314
FUN_0033046c
FUN_00330850
FUN_00331a68
FUN_00331c0c
FUN_00331ca4
FUN_00331f38
FUN_00334274
FUN_00334a4c
FUN_00334c34
FUN_00335ea4
FUN_00337274
FUN_0033780c
FUN_00337acc
FUN_00338284
FUN_00338b9c
FUN_00339ddc
FUN_0033a148
FUN_0033b9a8
FUN_0033c9b4
FUN_00340790
FUN_003432ec
FUN_0034894c
FUN_00348fa8
FUN_0034b684
FUN_0034b9e8
FUN_0034c544
FUN_0034eb88
FUN_0034fbec
FUN_0034fc4c
FUN_003565d0
FUN_0035689c
FUN_0035c508
FUN_0035cc2c
FUN_0035f640
FUN_00366af4
FUN_00366e0c
FUN_00367c10
FUN_00369acc
FUN_0036a158
FUN_0036a314
FUN_0036b730
FUN_0036d708
FUN_003734c4
FUN_003751d8
FUN_003774fc
FUN_00377a5c
FUN_00379c28
FUN_00383b18
append_385e1c
bad_alloc
bad_array_new_length
bad_cast
logic_error
operator__385ec4
runtime_error_385dbc
runtime_error_385dc8
streambuf
string_385e64
terminate
```

## Build log of this run (build/worklist.log)

```
[19:17:46] build 2026-10-18.1 on /Users/admin/glitchdecomp/fastpass 3/rewrite/pseudocode.c
[19:17:46] Resume check (30173 functions in manifest):
[19:17:46]   the rewrite changed since the last build — updating the split (functions whose code changed get the new code; the others keep their fixes)
[19:17:46]   [redo] split + header: input changed — rebuilding shared.h/globals.cpp and merging with the work already done
[19:17:47]   libclang reported 2 error(s) in the declarations (saved to libclang_parse_errors.txt), e.g.:
[19:17:47]     _parse_monolith.cpp:220: static assertion failed due to requirement 'sizeof(struct section) == 80': Ghidra's size of section
[19:17:47]     _parse_monolith.cpp:236: static assertion failed due to requirement 'sizeof(struct segment_command) == 72': Ghidra's size of segment_command
[19:17:53]   split -> 30173 function TUs, 65 types (+37 forward decls), 30173 prototypes, 0 globals
[19:18:06]     functions: 131 changed in the rewrite (new code taken), 311 already fixed by the model (kept), 29731 untouched (refreshed with the new split), 0 previously quarantined (restored for another try), 0 not in the old run
[19:18:06]     (the replaced versions are in /Users/admin/glitchdecomp/fastpass 3/snapshots/20261024-191755-build-update)
[19:18:06]   [redo] header check
[19:18:06]   » validate/repair shared headers
[19:18:07]   [redo] compile status
[19:18:07]   » preflight diagnose (surface any systemic cause before spending model time on 30173 functions)
[19:18:07]   preflight: sampled TUs compile — proceeding
[19:18:07]   » isolated compile sweep
[19:18:09]   compiling with 11 parallel worker(s)
[19:22:20]   isolated compile: 30098/30173 TUs pass, 75 need repair (252s)
[19:22:20]   status: 30098 compile, 75 still to fix, 0 quarantined
[19:25:36]   declared 120 name(s) the code uses that Ghidra's pseudocode has too (globals like DAT_..., library functions); compiling the 54 function(s) that use them again
[19:25:36]   compiling with 11 parallel worker(s)
[19:25:37]   isolated compile: 51/54 TUs pass, 3 need repair (1s)
[19:25:37]   LM Studio OK — using the loaded model qwen2.5-coder-3b-instruct-mlx
[19:25:37]   » dependency order + fixer loop
[19:25:37]   callgraph imported: 22076 callers, 64251 edges from callgraph.json
[19:25:37]   callgraph: 582 callee name(s) not in our TU set (external/library calls) — ignored for ordering
[19:25:37]   callgraph: exact deps for 21706/30173 functions
[19:25:38]     FUN_00214da4 -> fixed without the model
[19:25:38]     buildMenuGroupEntries_entry__16bb04 -> fixed without the model
[19:25:38]     FUN_002135c0 -> fixed without the model
[19:25:38]     applicationDidBecomeActive_ -> fixed without the model
[19:25:38]     FUN_001f3cd0 -> fixed without the model
[19:25:38]     initWithFrame__16c574 -> fixed without the model
[19:25:38]     dealloc_16c680 -> fixed without the model
[19:25:38]     FUN_001718c0 -> fixed without the model
[19:25:38]     FUN_001736b4 -> fixed without the model
[19:25:38]     FUN_00171a30 -> fixed without the model
[19:25:38]     FUN_001723a0 -> fixed without the model
[19:25:38]     createLayerTextureWithSize__16cb94 -> fixed without the model
[19:25:38]     invalidate_1a8a74 -> fixed without the model
[19:25:38]     updateLayerInRect__16ce54 -> fixed without the model
[19:25:38]     FUN_00173590 -> fixed without the model
[19:25:38]     setMarkedText_selectedRange_ -> fixed without the model
[19:25:38]     FUN_00171cc8 -> fixed without the model
[19:25:38]     FUN_001725c4 -> fixed without the model
[19:25:38]     FUN_001728ac -> fixed without the model
[19:25:38]     FUN_001a2588 -> fixed without the model
[19:25:38]     FUN_001a54e0 -> fixed without the model
[19:25:38]     drawRect__16d1bc -> fixed without the model
[19:25:38]     FUN_00173144 -> fixed without the model
[19:25:38]   quick fixes (no model): 23 of 24 function(s) compile now
[19:25:38]   fixer loop over 1 failing TU(s), dependency-ordered
[19:25:44]     [1/1] FUN_0029db84 -> fixed (5s)
[19:25:44]   learned fixes: 97 proven, 487 being tried, 159 retired (0 new this run); used 69 of 70 time(s) tried, 99% kept; 0 quarantined function(s) rescued. All in build/learned_fixes.txt
[19:25:44]   model: 2 small edit(s) asked for, 1 without a usable edit
[19:25:44]   fixer loop done: 30173 compiling, 0 quarantined
[19:25:44]   repair loop: 0 quarantined function(s) rescued
[19:27:54]   link round 1: linking 30176 objects ...
[19:27:56]   link round 1: 98 undefined, 0 duplicate symbol(s) — stubbed/quarantined, relinking
[19:27:57]   link round 2: linking 30177 objects ...
[19:27:58]   24 placeholder definition(s) in stubs.cpp (listed in link_report.txt)
[19:27:58]   LINK OK (round 2) -> /Users/admin/glitchdecomp/fastpass 3/build_c/program.dylib
[19:28:18]   privacy check: 275 possible identifying item(s) — final/ NOT updated (see privacy_report.txt, or --allow-privacy-findings)
```

## pipeline_state.json

```json
{
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 19:15:38",
      "at": "2026-10-24 19:16:00",
      "seconds": 23,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 19:16:03",
      "at": "2026-10-24 19:17:46",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 19:17:46",
      "at": "2026-10-24 19:22:20",
      "seconds": 274,
      "note": "30098/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 19:22:20",
      "at": "2026-10-24 19:25:45",
      "seconds": 205,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 3
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 19:25:45",
      "at": "2026-10-24 19:25:45",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 19:16:00",
      "at": "2026-10-24 19:16:03",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 19:25:45",
      "at": "2026-10-24 19:27:58",
      "seconds": 133,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 19:27:58",
      "at": "2026-10-24 19:28:04",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 19:28:04",
      "at": "2026-10-24 19:28:04",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": false,
      "started": "2026-10-24 19:28:04",
      "at": "2026-10-24 19:28:18",
      "note": "final/ not updated",
      "model": "qwen2.5-coder-3b-instruct-mlx"
    }
  },
  "version": "2026-10-25.8",
  "chars_per_token": {
    "ctx": 8192,
    "value": 2.06
  },
  "struggles": [
    {
      "at": "2026-10-24 17:30:59",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: instantiate (the plugin's factory and constructor run here)": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 17:54:17",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: instantiate (the plugin's factory and constructor run here)": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 18:26:45",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: load executable": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 18:56:17",
      "keys": {
        "rewrite|no usable rewrite: model returned no code (empty reply)": 3,
        "test|the rebuilt plugin didn't load: load executable": 1,
        "organize|the final C file doesn't build, so final/ wasn't written": 1,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 119,
        "link|functions replaced by placeholders to link": 24
      }
    },
    {
      "at": "2026-10-24 19:28:19",
      "keys": {
        "test|the rebuilt plugin didn't load: load executable": 1,
        "organize|possible identifying items left (final/ not written)": 275,
        "fix|Ghidra globals / library functions nothing declared (declared once in shared.h)": 120,
        "fix|fixes that undid each other (the cycle was stopped and the model got the function)": 1,
        "fix|small edits the model couldn't give a usable answer for": 1,
        "link|functions replaced by placeholders to link": 24
      }
    }
  ],
  "rates": [
    {
      "at": "10-23 10:48",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "learned_proven": 96,
      "learned_kept_pct": 100.0,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 17:30",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "learned_proven": 96,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 17:54",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 18:26",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "learned_proven": 96,
      "learned_kept_pct": 98.1,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 18:56",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "test_pass_pct": 0.0
    },
    {
      "at": "10-24 19:28",
      "functions": 30173,
      "compile_pct": 100.0,
      "quarantined_pct": 0.0,
      "to_fix": 0,
      "fix_tried": 1,
      "fix_success_pct": 100.0,
      "fix_per_hour": 23,
      "learned_proven": 97,
      "learned_kept_pct": 98.6,
      "test_pass_pct": 0.0
    }
  ]
}
```

## report.json

```json
{
  "generated": "2026-10-24 19:28:18",
  "pipeline_version": "2026-10-25.8",
  "workdir": "/Users/admin/glitchdecomp/fastpass 3",
  "export": {
    "functions": 30489,
    "with_pseudocode": 30489,
    "export_version": 2,
    "source": "headless-java",
    "datatypes": 205,
    "signatures": 30489
  },
  "rewrite": {
    "functions": 30489,
    "done": 30489,
    "stale": 12705,
    "skipped": 0,
    "too_big": 0,
    "not_started": 0,
    "renamed": 358,
    "tiny": 13364,
    "in_pieces": 3018,
    "faithful": 0,
    "suspect": 12726,
    "suspect_reasons": {
      "decompiler names left": 9244,
      "no real name": 7099,
      "invented text/printing": 3379,
      "some parts left as Ghidra wrote them": 626,
      "identifying strings left": 444,
      "cut off": 88,
      "raw addresses left": 29
    }
  },
  "build": {
    "functions": 30173,
    "compile": 30173,
    "quarantined": 0,
    "fixed_by_model": 155,
    "rederived": 2,
    "rederived_by": {
      "window-patch": 1,
      "faithful-pseudocode": 1
    }
  },
  "link": {
    "ok": true,
    "stubs": 19,
    "unresolved": 0
  },
  "improve": {},
  "organize": {
    "note": "final/ not updated",
    "written": false,
    "privacy_hits": 275
  },
  "stages": {
    "export": {
      "done": true,
      "started": "2026-10-24 19:15:38",
      "at": "2026-10-24 19:16:00",
      "seconds": 23,
      "note": "30489/30489 with pseudocode"
    },
    "rewrite": {
      "done": true,
      "started": "2026-10-24 19:16:03",
      "at": "2026-10-24 19:17:46",
      "seconds": 103,
      "model": "",
      "note": "30173/30489 rewritten",
      "model_busy": 12
    },
    "split": {
      "done": true,
      "started": "2026-10-24 19:17:46",
      "at": "2026-10-24 19:22:20",
      "seconds": 274,
      "note": "30098/30173 compile after the sweep"
    },
    "fix": {
      "done": true,
      "started": "2026-10-24 19:22:20",
      "at": "2026-10-24 19:25:45",
      "seconds": 205,
      "model": "qwen2.5-coder-3b-instruct-mlx",
      "model_busy": 3
    },
    "recover": {
      "done": true,
      "started": "2026-10-24 19:25:45",
      "at": "2026-10-24 19:25:45",
      "seconds": 0,
      "model": "qwen2.5-coder-3b-instruct-mlx"
    },
    "privacy": {
      "done": true,
      "started": "2026-10-24 19:16:00",
      "at": "2026-10-24 19:16:03",
      "seconds": 2,
      "note": "1141 replacement(s)"
    },
    "link": {
      "done": true,
      "started": "2026-10-24 19:25:45",
      "at": "2026-10-24 19:27:58",
      "seconds": 133,
      "note": "linked"
    },
    "test": {
      "done": false,
      "started": "2026-10-24 19:27:58",
      "at": "2026-10-24 19:28:04",
      "note": "the rebuilt plugin didn't load: load executable"
    },
    "improve": {
      "done": false,
      "started": "2026-10-24 19:28:04",
      "at": "2026-10-24 19:28:04",
      "note": "off (--improve turns it on)"
    },
    "organize": {
      "done": false,
      "started": "2026-10-24 19:28:04",
      "at": "2026-10-24 19:28:18",
      "note": "final/ not updated",
      "model": "qwen2.5-coder-3b-instruct-mlx"
    }
  }
}
```

## build_state.json

```json
{
  "input_sha": "7af29f67efd7eebd",
  "split_done": true,
  "header_ok": true,
  "sweep_done": true,
  "version": "2026-10-18.1",
  "link_ok": true
}
```
