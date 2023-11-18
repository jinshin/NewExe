# NewExe
NE (NewExe) segment manipulation tool

I needed to increase a segment in NE driver (EGA.DRV in Windows 3.0) and found out that there's no tools for that. For pure fun i made the tool to do this exact task. As documentation for old formats is vanishing, it might be useful for future software archeologists.
Good info: http://bytepointer.com/resources/win16_ne_exe_format_win3.0.htm
Resource size is actually in pages, not bytes
In device drivers resources are located after unmovable and undiscardable segments and they must be kept that way, or driver doesn't work - so i had to implement this exact behaviour, though simple EXE like SOL.EXE work fine with resources moved to end.
Anyway, this code is very beta, but worked on my test samples ok.
