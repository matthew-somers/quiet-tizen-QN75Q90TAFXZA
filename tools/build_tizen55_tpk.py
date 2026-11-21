#!/usr/bin/env python3
"""Build the standalone Tizen 5.5 Quiet Tizen TPK (org.quiettizen.home) for QN75Q90TAFXZA (T-NKMAKUC-2743.0)."""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
BUILD = LOCAL / "build-q90t"
TPK_ROOT = BUILD / "tpk-root"
RES_DIR = TPK_ROOT / "res"
BIN_DIR = TPK_ROOT / "bin"
LIB_DIR = TPK_ROOT / "lib"

APPLIBRARY_CS = """using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;

public sealed class LibraryApp
{
 public string Name {get;set;}
 public string Id {get;set;}
 public string Asset {get;set;}
 public string Description {get;set;}
 public string Fit {get;set;}
 public string Background {get;set;}
 public int Width {get;set;}
 public int Height {get;set;}
 public float[] Crop {get;set;}
 public bool Utility {get;set;}
 public LibraryApp()
 {
  Fit="cover";
  Background="#FFFFFF";
 }
}

public static class AppLibrary
{
 public const int Columns=5, Rows=3, PageSize=Columns*Rows;
 private static int Clamp(int v,int min,int max){return v<min?min:(v>max?max:v);}

 private static string ExtractString(string obj, string key)
 {
  string pat = "\\"" + key + "\\"";
  int idx = obj.IndexOf(pat, StringComparison.Ordinal);
  if (idx < 0) return null;
  int colon = obj.IndexOf(':', idx + pat.Length);
  if (colon < 0) return null;
  int q1 = obj.IndexOf('"', colon + 1);
  if (q1 < 0) return null;
  int q2 = q1 + 1;
  while (q2 < obj.Length)
  {
   if (obj[q2] == '"' && obj[q2 - 1] != '\\\\') break;
   q2++;
  }
  if (q2 >= obj.Length) return null;
  return obj.Substring(q1 + 1, q2 - q1 - 1);
 }

 private static int ExtractInt(string obj, string key, int defVal)
 {
  string pat = "\\"" + key + "\\"";
  int idx = obj.IndexOf(pat, StringComparison.Ordinal);
  if (idx < 0) return defVal;
  int colon = obj.IndexOf(':', idx + pat.Length);
  if (colon < 0) return defVal;
  int p = colon + 1;
  while (p < obj.Length && (obj[p] == ' ' || obj[p] == '\\t' || obj[p] == '\\r' || obj[p] == '\\n')) p++;
  int start = p;
  while (p < obj.Length && ((obj[p] >= '0' && obj[p] <= '9') || obj[p] == '-')) p++;
  int val;
  if (p > start && int.TryParse(obj.Substring(start, p - start), NumberStyles.Integer, CultureInfo.InvariantCulture, out val))
   return val;
  return defVal;
 }

 private static bool ExtractBool(string obj, string key, bool defVal)
 {
  string pat = "\\"" + key + "\\"";
  int idx = obj.IndexOf(pat, StringComparison.Ordinal);
  if (idx < 0) return defVal;
  int colon = obj.IndexOf(':', idx + pat.Length);
  if (colon < 0) return defVal;
  int p = colon + 1;
  while (p < obj.Length && (obj[p] == ' ' || obj[p] == '\\t' || obj[p] == '\\r' || obj[p] == '\\n')) p++;
  if (p + 4 <= obj.Length && string.Compare(obj, p, "true", 0, 4, StringComparison.OrdinalIgnoreCase) == 0) return true;
  if (p + 5 <= obj.Length && string.Compare(obj, p, "false", 0, 5, StringComparison.OrdinalIgnoreCase) == 0) return false;
  return defVal;
 }

 public static List<LibraryApp> Load(string path)
 {
  string raw = File.ReadAllText(path);
  var apps = new List<LibraryApp>();
  int pos = 0;
  while (pos < raw.Length)
  {
   int b1 = raw.IndexOf('{', pos);
   if (b1 < 0) break;
   int depth = 1;
   int b2 = b1 + 1;
   bool inStr = false;
   while (b2 < raw.Length && depth > 0)
   {
    char c = raw[b2];
    if (c == '"' && raw[b2 - 1] != '\\\\') inStr = !inStr;
    else if (!inStr)
    {
     if (c == '{') depth++;
     else if (c == '}') depth--;
    }
    b2++;
   }
   if (depth == 0)
   {
    string chunk = raw.Substring(b1, b2 - b1);
    var app = new LibraryApp();
    app.Name = ExtractString(chunk, "Name") ?? "";
    app.Id = ExtractString(chunk, "Id") ?? "";
    app.Asset = ExtractString(chunk, "Asset") ?? "";
    app.Description = ExtractString(chunk, "Description") ?? "";
    app.Fit = ExtractString(chunk, "Fit") ?? "cover";
    app.Background = ExtractString(chunk, "Background") ?? "#FFFFFF";
    app.Width = ExtractInt(chunk, "Width", 328);
    app.Height = ExtractInt(chunk, "Height", 184);
    app.Utility = ExtractBool(chunk, "Utility", false);
    if (!string.IsNullOrEmpty(app.Name) && !string.IsNullOrEmpty(app.Id) && !string.IsNullOrEmpty(app.Asset))
     apps.Add(app);
   }
   pos = b2;
  }
  return apps;
 }

 public static int PageCount(int count){return Math.Max(1,(count+PageSize-1)/PageSize);}
 public static int VisibleCount(int count,int page){return Math.Max(0,Math.Min(PageSize,count-page*PageSize));}
 public static int Move(int count,int absolute,string key)
 {
  if(count<=0)return -1;
  absolute=Clamp(absolute,0,count-1);
  int page=absolute/PageSize,local=absolute%PageSize,col=local%Columns,row=local/Columns;
  int pageStart=page*PageSize,visible=VisibleCount(count,page);
  if(key=="Left")return Math.Max(0,absolute-1);
  if(key=="Right")return Math.Min(count-1,absolute+1);
  if(key=="Up")
  {
   if(row>0)return absolute-Columns;
   if(page==0)return -1;
   return pageStart-Columns+col;
  }
  if(key=="Down")
  {
   if((row+1)*Columns<visible)return pageStart+Math.Min(local+Columns,visible-1);
   int next=pageStart+PageSize;
   return next<count?Math.Min(next+col,count-1):absolute;
  }
  return absolute;
 }
}
"""


def find_csc(explicit: str | None) -> str:
    if explicit:
        return explicit
    win_root = pathlib.Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidate = win_root / "Microsoft.NET" / "Framework64" / "v4.0.30319" / "csc.exe"
    if candidate.is_file():
        return str(candidate)
    found = shutil.which("csc") or shutil.which("mcs")
    if found:
        return found
    raise SystemExit("Could not find csc compiler. Pass --csc /path/to/csc.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--framework",
        type=pathlib.Path,
        default=LOCAL / "tv-framework-q90t",
        help="Directory containing extracted Tizen 5.5 framework DLLs (default: .local/tv-framework-q90t)",
    )
    parser.add_argument("--csc", help="Path to C# compiler (csc.exe)")
    args = parser.parse_args()

    fw = args.framework.resolve()
    if not (fw / "Tizen.NUI.dll").is_file():
        parser.error(f"Missing Tizen.NUI.dll in {fw}. Pull the TV's framework assemblies first.")

    csc = find_csc(args.csc)
    LOCAL.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    # 1. Write default apps.local.json if not already customized
    apps_local_path = ROOT / "launcher" / "assets" / "apps.local.json"
    if not apps_local_path.is_file():
        apps_local = [
            {
                "Name": "YouTube",
                "Id": "9Ur5IzDKqV.TizenYouTube",
                "Asset": "app-icons/youtube-card.svg",
                "Description": "Videos & subscriptions",
                "Fit": "cover",
                "Background": "#FF0000",
                "Width": 640,
                "Height": 360,
            },
            {
                "Name": "Samsung Settings",
                "Id": "org.tizen.menu",
                "Asset": "quick-settings.svg",
                "Description": "Full TV settings menu",
                "Fit": "cover",
                "Background": "#2C3558",
                "Width": 410,
                "Height": 286,
            },
            {
                "Name": "Device Care",
                "Id": "qtMHjALHus.TVDeviceCare",
                "Asset": "quick-network.svg",
                "Description": "Diagnostics & storage",
                "Fit": "cover",
                "Background": "#246076",
                "Width": 410,
                "Height": 286,
            },
            {
                "Name": "Get more apps",
                "Id": "org.volt.apps",
                "Asset": "glass-button.svg",
                "Description": "Open Samsung Apps",
                "Fit": "cover",
                "Background": "#EEF0F8",
                "Width": 100,
                "Height": 112,
                "Utility": True,
            },
        ]
        apps_local_path.write_text(json.dumps(apps_local, indent=2) + "\n", encoding="utf-8")

    (LOCAL / "AppLibraryQ90T.cs").write_text(APPLIBRARY_CS, encoding="utf-8")

    # 2. Transform launcher/src/Home.cs for Tizen 5.5 QN75Q90TAFXZA
    src = (ROOT / "launcher" / "src" / "Home.cs").read_text(encoding="utf-8")

    old_root = ' const string Root="/opt/usr/apps/com.samsung.tv.bixby-promotion/res/quiet-home/";'
    new_root = """ static string ResolveRoot(){
  try{
   string r=Application.Current.DirectoryInfo.Resource;
   if(!string.IsNullOrEmpty(r)){
    if(!r.EndsWith("/"))r+="/";
    if(File.Exists(r+"apps.json"))return r;
    if(File.Exists(r+"quiet-home/apps.json"))return r+"quiet-home/";
   }
  }catch{}
  if(File.Exists("/opt/usr/apps/org.quiettizen.home/res/apps.json"))return "/opt/usr/apps/org.quiettizen.home/res/";
  if(File.Exists("/opt/usr/home/owner/share/quiet-home/apps.json"))return "/opt/usr/home/owner/share/quiet-home/";
  return "/opt/usr/apps/com.samsung.tv.bixby-promotion/res/quiet-home/";
 }
 string Root=ResolveRoot();"""
    src = src.replace(old_root, new_root)
    src = src.replace(
        "  base.OnCreate();\n",
        '  base.OnCreate();\n  Root=ResolveRoot();\n  try{if(File.Exists("/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-theme.txt"))darkMode=File.ReadAllText("/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-theme.txt").Trim()!="light";}catch{}\n',
    )

    old_colors = """ readonly Color ink=new Color(0.114f,0.114f,0.122f,1);
 readonly Color muted=new Color(0.431f,0.431f,0.451f,1);
 readonly Color white=new Color(1,1,1,1);
 readonly Color accent=new Color(0.24f,0.29f,0.72f,1);"""
    new_colors = """ bool darkMode=true;
 Color ink{get{return darkMode?new Color(0.945f,0.961f,0.976f,1):new Color(0.114f,0.114f,0.122f,1);}}
 Color muted{get{return darkMode?new Color(0.580f,0.639f,0.722f,1):new Color(0.431f,0.431f,0.451f,1);}}
 readonly Color white=new Color(1,1,1,1);
 Color accent{get{return darkMode?new Color(0.376f,0.647f,0.980f,1):new Color(0.24f,0.29f,0.72f,1);}}"""
    src = src.replace(old_colors, new_colors)

    src = src.replace(
        "int page, selected, area=1, lastSource=14;",
        "int page, selected, area=1, lastSource=16, currentVoice=-1, currentSpeaker=-1;\n bool isPaused=false;\n long openedAt=0;",
    )
    src = src.replace(
        '[DllImport("libvconf.so.0")] static extern int vconf_get_int(string key,out int value);',
        '[DllImport("libvconf.so.0")] static extern int vconf_get_int(string key,out int value);\n'
        ' [DllImport("libvconf.so.0")] static extern int vconf_get_bool(string key,out int value);\n'
        ' [DllImport("libvconf.so.0")] static extern int vconf_set_bool(string key,int value);\n'
        ' [DllImport("libcapi-media-sound-manager-tv.so.0")] static extern int sound_manager_get_speaker_selection(out int speaker);\n'
        ' [DllImport("libcapi-media-sound-manager-tv.so.0")] static extern int sound_manager_set_speaker_selection(int speaker);',
    )
    src = src.replace(
        'void RefreshSource(){try{int n;if(vconf_get_int("memory/system/source_type",out n)==0&&n>=13&&n<=15)lastSource=n;}catch{}}',
        'void RefreshSource(){try{int n;if(vconf_get_int("memory/system/source_type",out n)==0&&n>=13&&n<=16)lastSource=n;}catch{}}',
    )
    src = src.replace(
        "int SourceIndex(){return lastSource==15?1:lastSource==13?2:0;}",
        "int SourceIndex(){return lastSource==14?1:lastSource==13?2:0;}",
    )

    old_page0_and_2 = """  if(page==0){
   var hero=Feature("PlayStation 5","hdmi:14","Game console · HDMI 2","feature-ps5.svg",80,262,1040,442,"hero");
   hero.Card.Add(Label("PLAYSTATION 5",44,52,550,40,24,new Color(.86f,.91f,1,1),"Semibold"));
   hero.Card.Add(Label("Let's play.",40,124,560,100,72,white,"Display"));
   hero.Card.Add(Label("Switch to HDMI 2",46,246,440,48,30,new Color(.88f,.93f,1,1)));
   Feature("Nintendo Switch","hdmi:15","Game console · HDMI 3","feature-switch.svg",1160,262,320,442,"portrait");
   Feature("HDMI 1","hdmi:13","External device","feature-hdmi.svg",1520,262,320,442,"portrait");
  }else if(page==1){
   BuildLibrary();
  }else{
   RefreshSettings();
   SettingsTile("Volume","volume","Select · Left / Right to adjust","volume",0,0);
   SettingsTile("Brightness","brightness","Select · Left / Right to adjust","brightness",1,0);
   SettingsTile("Game Mode","game-mode","Select to switch on or off","game",2,0);
   SettingsTile("Sleep Timer","sleeptimer","Select to change the timer","sleep",3,0);
   SettingsTile("Sound","mute","Select to mute or unmute","mute",0,1);
   SettingsTile("Controllers","controllers","DualSense · hold PS + Create","controller",1,1);
   SettingsTile("Network","network","Wi-Fi and connection setup","network",2,1);
   SettingsTile("Advanced","app:org.tizen.menu","Open Samsung's full settings","settings",3,1);
  }
  if(page==0){
  Add(new ImageView{ResourceUrl=Root+"glass-shelf.svg",Position2D=new Position2D(0,784),Size2D=new Size2D(1920,280)});
  Dock("Netflix","app:org.tizen.netflix-app","netflix",0);
  Dock("YouTube","app:com.samsung.tv.cobalt-yt","youtube",1);
  Dock("Prime Video","app:org.tizen.primevideo","prime",2);
  Dock("PlayStation 5","hdmi:14","ps5",3);
  Dock("Nintendo Switch","hdmi:15","switch",4);
  Dock("Your Apps","page:1","apps",5);
  }"""

    new_page0_and_2 = """  if(page==0){
   RefreshSettings();
   var hero=Feature("PC Monitor","hdmi:16","PC · HDMI 4","feature-pc.svg",80,262,1040,442,"hero");
   hero.Card.Add(Label("PC MONITOR",44,52,550,40,24,new Color(.86f,.91f,1,1),"Semibold"));
   hero.Card.Add(Label("Switch to HDMI 4",46,246,440,48,30,new Color(.88f,.93f,1,1)));
   hero.FocusRing.RaiseToTop();
   Feature("Game Consoles","hdmi:14","Consoles · HDMI 2","feature-consoles.svg",1160,262,320,442,"portrait");
   Feature("Chromecast","hdmi:13","Streaming · HDMI 1","feature-hdmi.svg",1520,262,320,442,"portrait");
  }else if(page==1){
   BuildLibrary();
  }else{
   RefreshSettings();
   SettingsTile("Volume","volume","eARC Soundbar · Left / Right","volume",0,0);
   SettingsTile("Brightness","brightness","Select · Left / Right to adjust","brightness",1,0);
   SettingsTile("Game Mode","game-mode","Select to switch on or off","game",2,0);
   SettingsTile("Sleep Timer","sleeptimer","Select to change the timer","sleep",3,0);
   SettingsTile("Sound Output","sound-output","Select to switch audio output","mute",0,1);
   SettingsTile("Voice Control","voice","Select to enable or disable voice","voice",1,1);
   SettingsTile("Network & BT","network","Wi-Fi and Bluetooth setup","network",2,1);
   SettingsTile("Advanced","app:org.tizen.menu","Open Samsung's full settings","settings",3,1);
  }
  if(page==0){
  Add(new ImageView{ResourceUrl=Root+(darkMode?"glass-shelf-dark.svg":"glass-shelf.svg"),Position2D=new Position2D(0,784),Size2D=new Size2D(1920,280)});
  Dock("YouTube","app:9Ur5IzDKqV.TizenYouTube","youtube",0);
  Dock("Sound Output","sound-output","sound",1);
  Dock("PC · HDMI 4","hdmi:16","pc",2);
  Dock("Consoles · HDMI 2","hdmi:14","consoles",3);
  Dock("Voice Control","voice","voice",4);
  Dock("Quick Settings","page:2","settings",5);
  }"""
    src = src.replace(old_page0_and_2, new_page0_and_2)

    src = src.replace(
        'Add(new ImageView{ResourceUrl=Root+"free-background.svg",Size2D=new Size2D(1920,1080)});',
        'Tizen.NUI.Window.Instance.BackgroundColor=darkMode?new Color(0.043f,0.055f,0.078f,1):new Color(0.96f,0.96f,0.97f,1);\n  Add(new ImageView{ResourceUrl=Root+(darkMode?"free-background-dark.svg":"free-background.svg"),Size2D=new Size2D(1920,1080)});',
    )
    src = src.replace(
        'clock=Text(DateTime.Now.ToString("h:mm tt"),1540,170,300,45,24,muted);',
        'clock=Text(DateTime.Now.ToString("h:mm tt"),1180,170,300,45,24,muted);',
    )
    src = src.replace(
        'Toolbar("Apps","page:1","apps",0);Toolbar("Inputs","page:0","hdmi",1);Toolbar("Settings","page:2","settings",2);',
        'Toolbar("Apps","page:1","apps",0);Toolbar("Inputs","page:0","hdmi",1);Toolbar("Settings","page:2","settings",2);Toolbar(darkMode?"Light Mode":"Dark Mode","theme","theme",3);',
    )
    src = src.replace(
        'toolbarHint=Text("",1530,170,310,45,24,ink);',
        'toolbarHint=Text("",1170,170,310,45,24,ink);',
    )
    old_toolbar = """ void Toolbar(string label,string action,string icon,int n)
 {
  int x=1596+n*88;
  var card=Panel(x+34,103,68,68,new Color(0,0,0,0),34);card.PivotPoint=new Position(.5f,.5f,.5f);card.PositionUsesPivotPoint=true;
  card.Add(new ImageView{ResourceUrl=Root+"glass-button.svg",Position2D=new Position2D(-16,-16),Size2D=new Size2D(100,112)});
  card.Add(new ImageView{ResourceUrl=Root+"symbol-"+icon+".png",Color=ink,Position2D=new Position2D(19,19),Size2D=new Size2D(30,30)});
  slots.Add(new Slot{Card=card,Name=label,Action=action,Description=label,Row=-1,X=x,Y=69,W=68,H=68});
 }"""
    new_toolbar = """ void Toolbar(string label,string action,string icon,int n)
 {
  int x=1508+n*88;
  var card=Panel(x+34,103,68,68,new Color(0,0,0,0),34);card.PivotPoint=new Position(.5f,.5f,.5f);card.PositionUsesPivotPoint=true;
  card.Add(new ImageView{ResourceUrl=Root+(darkMode?"glass-button-dark.svg":"glass-button.svg"),Position2D=new Position2D(-16,-16),Size2D=new Size2D(100,112)});
  if(icon=="theme")card.Add(new ImageView{ResourceUrl=Root+(darkMode?"symbol-theme-dark.svg":"symbol-theme-light.svg"),Position2D=new Position2D(19,19),Size2D=new Size2D(30,30)});
  else card.Add(new ImageView{ResourceUrl=Root+"symbol-"+icon+".png",Color=ink,Position2D=new Position2D(19,19),Size2D=new Size2D(30,30)});
  var ring=new ImageView{ResourceUrl=Root+"focus-toolbar.svg",Size2D=new Size2D(68,68),Opacity=0};card.Add(ring);
  slots.Add(new Slot{Card=card,FocusRing=ring,Name=label,Action=action,Description=label,Row=-1,X=x,Y=69,W=68,H=68});
 }"""
    src = src.replace(old_toolbar, new_toolbar)
    src = src.replace(
        '  slots.Add(new Slot{Card=card,Label=value,Name=name,Action=action,Description=description,Row=row,X=x,Y=y,W=w,H=h});',
        '  var ring=new ImageView{ResourceUrl=Root+"focus-tile.svg",Size2D=new Size2D(w,h),Opacity=0};card.Add(ring);\n  slots.Add(new Slot{Card=card,FocusRing=ring,Label=value,Name=name,Action=action,Description=description,Row=row,X=x,Y=y,W=w,H=h});',
    )
    src = src.replace(
        '  var slot=new Slot{Card=card,Shadow=shadow,Label=caption,Name=label,Action=action,Description=description,Row=0,X=x,Y=y,W=w,H=h};slots.Add(slot);return slot;',
        '  var ring=new ImageView{ResourceUrl=Root+"focus-"+shape+".svg",Size2D=new Size2D(w,h),Opacity=0};card.Add(ring);\n  var slot=new Slot{Card=card,Shadow=shadow,FocusRing=ring,Label=caption,Name=label,Action=action,Description=description,Row=0,X=x,Y=y,W=w,H=h};slots.Add(slot);return slot;',
    )
    old_dock = """ void Dock(string label,string action,string asset,int n)
 {
  int x=(int)Math.Round(80+n*(253.333+48));
  var shadow=Add(new ImageView{ResourceUrl=Root+"shadow-dock.svg",Position2D=new Position2D(x-24,842),Size2D=new Size2D(301,190)});
  var card=Panel(x+126,917,253,126,new Color(0,0,0,0),22);card.PivotPoint=new Position(.5f,.5f,.5f);card.PositionUsesPivotPoint=true;
  var official=library.Find(a=>a.Id==action.Substring(action.IndexOf(':')+1));
  if(official!=null){card.BackgroundColor=HexColor(official.Background);AddAppArtwork(card,official,253,126);}
  else card.Add(new ImageView{ResourceUrl=Root+"free-dock-"+asset+".svg",Size2D=new Size2D(253,126)});
  slots.Add(new Slot{Card=card,Shadow=shadow,Name=label,Action=action,Description=label,Row=1,X=x,Y=854,W=253,H=126});
 }"""
    new_dock = """ void Dock(string label,string action,string asset,int n)
 {
  int x=(int)Math.Round(80+n*(253.333+48));
  var shadow=Add(new ImageView{ResourceUrl=Root+"shadow-dock.svg",Position2D=new Position2D(x-24,842),Size2D=new Size2D(301,190)});
  var card=Panel(x+126,917,253,126,new Color(0,0,0,0),22);card.PivotPoint=new Position(.5f,.5f,.5f);card.PositionUsesPivotPoint=true;
  var official=action.IndexOf(':')>=0?library.Find(a=>a.Id==action.Substring(action.IndexOf(':')+1)):null;
  if(official!=null){card.BackgroundColor=HexColor(official.Background);AddAppArtwork(card,official,253,126);}
  else card.Add(new ImageView{ResourceUrl=Root+"free-dock-"+asset+".svg",Size2D=new Size2D(253,126)});
  TextLabel valLabel=null;
  if(action=="sound-output"){
   card.Add(Label("SOUND OUTPUT",18,16,217,26,16,new Color(.82f,.92f,1f,1),"Semibold"));
   valLabel=Label(ShortSpeakerName(),18,46,217,44,25,white,"Display");
   card.Add(valLabel);
   card.Add(Label("Select to switch",18,92,217,22,14,new Color(.80f,.90f,1f,.88f)));
  }
  var ring=new ImageView{ResourceUrl=Root+"focus-dock.svg",Size2D=new Size2D(253,126),Opacity=0};card.Add(ring);
  slots.Add(new Slot{Card=card,Shadow=shadow,FocusRing=ring,Label=valLabel,Name=label,Action=action,Description=label,Row=1,X=x,Y=854,W=253,H=126});
 }"""
    src = src.replace(old_dock, new_dock)
    src = src.replace(
        'var ring=new View{Size2D=new Size2D(w,h),BackgroundColor=new Color(0,0,0,0),CornerRadius=new Vector4(18,18,18,18),BorderlineWidth=4,BorderlineColor=accent,Opacity=0};',
        'var ring=new ImageView{ResourceUrl=Root+"focus-app.svg",Size2D=new Size2D(w,h),Opacity=0};',
    )
    src = src.replace(
        "if(area==0){int next=page+d;if(next<0||next>2){area=3;selected=Row(-1)[next<0?2:0];UpdateFocus();}else{page=next;selected=0;BuildPage();}}",
        "if(area==0){int next=page+d;if(next<0||next>2){var r=Row(-1);area=3;selected=r[next<0?r.Count-1:0];UpdateFocus();}else{page=next;selected=0;BuildPage();}}",
    )
    src = src.replace(
        'for(int i=0;i<3;i++){tabs[i].TextColor=i==page?ink:muted;tabs[i].FontFamily="Quiet Inter "+(i==page?"Semibold":"Medium");tabs[i].BackgroundColor=area==0&&i==page?new Color(1,1,1,.7f):new Color(0,0,0,0);tabs[i].CornerRadius=new Vector4(34,34,34,34);}',
        'for(int i=0;i<3;i++){bool tf=area==0&&i==page;tabs[i].TextColor=tf?white:(i==page?ink:muted);tabs[i].FontFamily="Quiet Inter "+(i==page?"Semibold":"Medium");tabs[i].BackgroundColor=tf?accent:(i==page?(darkMode?new Color(1,1,1,.10f):new Color(0,0,0,.06f)):new Color(0,0,0,0));}',
    )
    src = src.replace(
        'if(s.FocusRing!=null)s.FocusRing.Opacity=f?1:0;\n    if(s.Label!=null&&page!=2)s.Label.FontFamily="Quiet Inter "+(f?"Semibold":"Medium");',
        'if(s.FocusRing!=null){s.FocusRing.Opacity=f?1:0;if(f)s.FocusRing.RaiseToTop();}\n    if(s.Action=="sound-output"&&s.Label!=null)s.Label.Text=ShortSpeakerName();\n    else if(s.Label!=null&&page!=2){s.Label.FontFamily="Quiet Inter "+(f?"Semibold":"Medium");s.Label.TextColor=f?accent:ink;}',
    )

    old_artwork_block = """ void AddAppArtwork(View card,LibraryApp app,int w,int h)
 {
  if(!app.Utility){
   var cached=GetArtwork(app,w,h);
   if(cached.Image.LoadingStatus!=ImageView.LoadingStatusType.Ready)pageArtworkCold++;
   cached.Parent.Remove(cached.Image);card.Add(cached.Image);cached.Parent=card;
  }
  if(app.Utility){
   card.Add(new View{Position2D=new Position2D(w/2-28,h/2-2),Size2D=new Size2D(56,4),BackgroundColor=ink});
   card.Add(new View{Position2D=new Position2D(w/2-2,h/2-28),Size2D=new Size2D(4,56),BackgroundColor=ink});
  }
 }
 void PreloadArtwork()
 {
  // Keep the real image views alive on the scene; moving between pages never
  // destroys their decoded textures. The zero-opacity parent is never drawn.
  artworkPreloadRoot=new View{Size2D=new Size2D(1920,1080),Opacity=0};
  Window.Default.Add(artworkPreloadRoot);
  foreach(var app in library)if(!app.Utility)GetArtwork(app,328,184);
  foreach(var id in new[]{"org.tizen.netflix-app","com.samsung.tv.cobalt-yt","org.tizen.primevideo"}){
   var app=library.Find(a=>a.Id==id);if(app!=null)GetArtwork(app,253,126);
  }
 }"""
    new_artwork_block = """ void AddAppArtwork(View card,LibraryApp app,int w,int h)
 {
  if(!app.Utility){
   card.Add(new ImageView{ResourceUrl=Root+app.Asset,Size2D=new Size2D(w,h)});
   artworkViewsCreated++;
  }
  if(app.Utility){
   if(darkMode)card.BackgroundColor=new Color(0.118f,0.149f,0.220f,1);
   card.Add(new View{Position2D=new Position2D(w/2-28,h/2-2),Size2D=new Size2D(56,4),BackgroundColor=ink});
   card.Add(new View{Position2D=new Position2D(w/2-2,h/2-28),Size2D=new Size2D(4,56),BackgroundColor=ink});
  }
 }
 void PreloadArtwork()
 {
  artworkPreloadRoot=new View{Size2D=new Size2D(1,1),Opacity=0};
 }"""
    src = src.replace(old_artwork_block, new_artwork_block)

    src = src.replace(
        'slots[4].Label.Text=currentMute<0?"Unavailable":currentMute==1?"Muted":"Sound on";',
        'slots[4].Label.Text=ShortSpeakerName();',
    )
    src = src.replace(
        'slots[5].Label.Text="Pair controller";',
        'slots[5].Label.Text=currentVoice<0?"Voice settings":currentVoice==1?"Voice on":"Voice off";',
    )

    old_activate = '  if(a=="controllers"){Launch("org.tizen.menu","add-bluetooth-keyboard");return;}'
    new_activate = """  if(a=="theme"){
   darkMode=!darkMode;
   try{File.WriteAllText("/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-theme.txt",darkMode?"dark":"light");}catch{}
   BuildPage();
   WriteState("theme:"+(darkMode?"dark":"light"));
   return;
  }
  if(a=="sound-output"){
   CycleSoundOutput();
   return;
  }
  if(a=="voice"){
   RefreshSettings();
   int target=currentVoice==1?0:1;
   int r1=-1,r2=-1;
   try{
    r1=vconf_set_bool("db/si_service/voice_recog_enable",target);
    r2=vconf_set_bool("db/multi-assistant/prelaunch_mode",target);
   }catch{r1=-1;}
   RefreshSettings();
   if(r1==0&&currentVoice==target){
    if(page==2)UpdateFocus();
    else ShowError("Voice Control "+(currentVoice==1?"enabled":"disabled")+".");
    WriteState("voice_changed:"+currentVoice);
   }else{
    Launch("org.tizen.menu","voice");
   }
   return;
  }
  if(a=="controllers"){Launch("org.tizen.menu","add-bluetooth-keyboard");return;}"""
    src = src.replace(old_activate, new_activate)

    src = src.replace(
        "foreach(var v in scene){Window.Default.Remove(v);v.Dispose();}scene.Clear();slots.Clear();",
        "foreach(var v in scene){Window.Default.Remove(v);v.Dispose();}scene.Clear();slots.Clear();notice=null;detail=null;clock=null;toolbarHint=null;",
    )
    src = src.replace(
        "void ShowError(string text){notice.Text=text;}",
        "void ShowError(string text){try{if(notice!=null)notice.Text=text;}catch{}}",
    )
    src = src.replace(
        "currentVolume=sound_manager_get_master_volume(out var v)==0?v:-1;",
        "currentVolume=-1;try{int v_vol;if(sound_manager_get_master_volume(out v_vol)==0)currentVolume=v_vol;}catch{}",
    )
    src = src.replace(
        "currentMute=sound_manager_get_master_mute(out var m)==0?m:-1;",
        "currentMute=-1;try{int m_mute;if(sound_manager_get_master_mute(out m_mute)==0)currentMute=m_mute;}catch{}\n  currentVoice=-1;try{int v_voice;if(vconf_get_bool(\"db/si_service/voice_recog_enable\",out v_voice)==0)currentVoice=v_voice;}catch{}\n  currentSpeaker=-1;try{int v_spk;if(sound_manager_get_speaker_selection(out v_spk)==0)currentSpeaker=v_spk;}catch{}",
    )
    src = src.replace(
        'foreach(var id in new[]{"brightness","game-mode","sleeptimer"}){',
        'foreach(var id in new[]{"brightness","game-mode","sleeptimer","soundoutput"}){',
    )
    src = src.replace(
        "void ChangeVolume(int delta){int n;int r=sound_manager_get_master_volume(out n);if(r==0)r=sound_manager_set_master_volume(Math.Max(0,Math.Min(100,n+delta)));if(r!=0)ShowError(\"Use the remote's volume buttons.\");RefreshSettings();UpdateFocus();WriteState(\"volume_changed\");}",
        "string ShortSpeakerName(){\n"
        " string sn=SettingName(\"soundoutput\");\n"
        " if(!string.IsNullOrEmpty(sn)&&sn!=\"Unavailable\"){\n"
        "  if(sn.IndexOf(\"eARC\",StringComparison.OrdinalIgnoreCase)>=0||sn.IndexOf(\"ARC\",StringComparison.OrdinalIgnoreCase)>=0||sn.IndexOf(\"Receiver\",StringComparison.OrdinalIgnoreCase)>=0)return \"HDMI eARC\";\n"
        "  if(sn.IndexOf(\"TV\",StringComparison.OrdinalIgnoreCase)>=0)return \"TV Speaker\";\n"
        "  if(sn.IndexOf(\"Optical\",StringComparison.OrdinalIgnoreCase)>=0||sn.IndexOf(\"Audio Out\",StringComparison.OrdinalIgnoreCase)>=0)return \"Optical\";\n"
        "  if(sn.IndexOf(\"Bluetooth\",StringComparison.OrdinalIgnoreCase)>=0||sn.IndexOf(\"BT\",StringComparison.OrdinalIgnoreCase)>=0)return \"Bluetooth\";\n"
        "  return sn.Length>15?sn.Substring(0,15):sn;\n"
        " }\n"
        " if(currentSpeaker==0)return \"TV Speaker\";\n"
        " if(currentSpeaker==1)return \"Optical\";\n"
        " if(currentSpeaker==2||currentSpeaker==3)return \"HDMI eARC\";\n"
        " if(currentSpeaker==4||currentSpeaker==5)return \"Bluetooth\";\n"
        " return currentSpeaker>=0?\"Speaker \"+currentSpeaker:\"HDMI eARC\";\n"
        "}\n"
        " void CycleSoundOutput(){\n"
        "  RefreshSettings();\n"
        "  int oldSpk=currentSpeaker;\n"
        "  string oldVal=SettingValue(\"soundoutput\");\n"
        "  int[] order=new[]{2,0,1};\n"
        "  bool switched=false;\n"
        "  int startIdx=0;\n"
        "  for(int i=0;i<order.Length;i++)if(order[i]==oldSpk){startIdx=i;break;}\n"
        "  for(int step=1;step<=order.Length;step++){\n"
        "   int candidate=order[(startIdx+step)%order.Length];\n"
        "   if(candidate==oldSpk)continue;\n"
        "   int sr=-1;\n"
        "   try{sr=sound_manager_set_speaker_selection(candidate);}catch{sr=-1;}\n"
        "   try{CSharpSetItemValue(\"soundoutput\",candidate.ToString());}catch{}\n"
        "   RefreshSettings();\n"
        "   if(currentSpeaker!=oldSpk||SettingValue(\"soundoutput\")!=oldVal){switched=true;break;}\n"
        "  }\n"
        "  UpdateFocus(false);\n"
        "  if(switched){\n"
        "   ShowError(\"Sound Output: \"+ShortSpeakerName());\n"
        "   WriteState(\"speaker_changed:\"+currentSpeaker+\":\"+SettingValue(\"soundoutput\"));\n"
        "  }else{\n"
        "   WriteState(\"speaker_popup:\"+currentSpeaker+\":\"+SettingValue(\"soundoutput\"));\n"
        "   Launch(\"org.tizen.volume-setting\");\n"
        "  }\n"
        " }\n"
        " void ChangeVolume(int delta){int n=0,r=-1;try{r=sound_manager_get_master_volume(out n);if(r==0)r=sound_manager_set_master_volume(Math.Max(0,Math.Min(100,n+delta)));}catch{r=-1;}if(r!=0)ShowError(\"Use the remote's volume buttons.\");RefreshSettings();UpdateFocus();WriteState(\"volume_changed\");}",
    )
    src = src.replace(
        'if(a=="mute"){int n;int r=sound_manager_get_master_mute(out n);if(r==0)r=sound_manager_set_master_mute(n==1?0:1);if(r!=0)ShowError("Use the remote\'s mute button.");RefreshSettings();UpdateFocus();WriteState("mute_changed");}',
        'if(a=="mute"){int n=0,r=-1;try{r=sound_manager_get_master_mute(out n);if(r==0)r=sound_manager_set_master_mute(n==1?0:1);}catch{r=-1;}if(r!=0)ShowError("Use the remote\'s mute button.");RefreshSettings();UpdateFocus();WriteState("mute_changed");return;}',
    )
    src = src.replace(
        'else if(k=="XF86Back"||k=="Back"||k=="Escape"||k=="XF86Exit")SelectSource(lastSource);',
        'else if(k=="XF86Back"||k=="Back"||k=="Escape"||k=="XF86Exit")CloseLauncher();',
    )
    src = src.replace(
        'void SelectSource(int source){int r=connect_source(source);if(r<0){ShowError("Input could not be switched. Open Advanced settings to check the connection.");WriteState("source_failed:"+r);return;}lastSource=source;Launch("org.tizen.tv-viewer");}',
        'bool CheckExternalCommand(){const string cf="/home/owner/share/tmp/sdk_tools/quiet-home-cmd.txt";try{if(File.Exists(cf)){string cmd=File.ReadAllText(cf).Trim();try{File.Delete(cf);}catch{}if(cmd.StartsWith("hdmi:")){SelectSource(int.Parse(cmd.Substring(5)));return true;}}}catch{}return false;}\n'
        ' void CloseLauncher(){isPaused=true;int cur=-1;try{if(vconf_get_int("memory/system/source_type",out cur)!=0)cur=-1;}catch{cur=-1;}if(cur>=13&&cur<=16){lastSource=cur;WriteState("close_to_current_source:"+cur);Launch("org.tizen.tv-viewer");return;}SelectSource(lastSource);}\n'
        ' void SelectSource(int source){int cur=-1;try{if(vconf_get_int("memory/system/source_type",out cur)!=0)cur=-1;}catch{cur=-1;}if(cur==source){lastSource=source;isPaused=true;WriteState("already_on_source:"+source);Launch("org.tizen.tv-viewer");return;}lastSource=source;isPaused=true;Launch("org.tizen.tv-viewer");int r=-1;try{r=connect_source(source);}catch(Exception ex){ShowError("HDMI switch error: "+ex.Message);WriteState("source_ex:"+ex.GetType().Name);return;}if(r<0){ShowError("Input could not be switched ("+r+").");WriteState("source_failed:"+r);return;}WriteState("switched_source:"+source);}',
    )
    src = src.replace(
        'clockTimer.Start();WriteState("created");',
        'isPaused=false;openedAt=(long)Environment.TickCount;clockTimer.Start();WriteState("created");CheckExternalCommand();',
    )
    src = src.replace(
        'protected override void OnPause(){base.OnPause();',
        'protected override void OnPause(){base.OnPause();isPaused=true;',
    )
    src = src.replace(
        'protected override void OnResume(){base.OnResume();RefreshSource();if(tabs!=null&&page==2){RefreshSettings();UpdateFocus(false);}WriteState("resumed");}',
        'protected override void OnResume(){base.OnResume();if(CheckExternalCommand())return;if(isPaused){isPaused=false;openedAt=(long)Environment.TickCount;}if(clockTimer!=null)clockTimer.Start();RefreshSource();if(tabs!=null&&(page==2||page==0)){RefreshSettings();UpdateFocus(false);}WriteState("resumed");}',
    )
    src = src.replace(
        'protected override void OnAppControlReceived(AppControlReceivedEventArgs e){base.OnAppControlReceived(e);string requested; if(e.ReceivedAppControl.ExtraData.TryGet("quiet_page",out requested)&&requested=="settings")OpenSettings("settings_request");else if(requested=="apps"){page=1;area=1;selected=0;BuildPage();}else Home("home_request");}',
        'protected override void OnAppControlReceived(AppControlReceivedEventArgs e){base.OnAppControlReceived(e);if(CheckExternalCommand())return;string requested;bool hasPage=e.ReceivedAppControl.ExtraData.TryGet("quiet_page",out requested);if(hasPage&&requested=="settings"){isPaused=false;openedAt=(long)Environment.TickCount;OpenSettings("settings_request");}else if(hasPage&&requested=="apps"){isPaused=false;openedAt=(long)Environment.TickCount;page=1;area=1;selected=0;BuildPage();}else{if(!isPaused&&((long)Environment.TickCount-openedAt)>500){WriteState("home_toggle_close");CloseLauncher();return;}isPaused=false;openedAt=(long)Environment.TickCount;Home("home_request");}}',
    )
    src = src.replace(
        'if(k=="XF86Home"){Home("home_key");return;}',
        'if(k=="XF86DiscretHDMI4"){SelectSource(16);return;}\n    if(k=="XF86Home"){if(CheckExternalCommand())return;if(((long)Environment.TickCount-openedAt)>500){WriteState("home_key_close");CloseLauncher();return;}Home("home_key");return;}',
    )

    old_launch_method = """ void Launch(string id,string menuItem=null)
 {
  IntPtr c;int r=app_control_create(out c);if(r!=0){ShowError("Could not open the app.");return;}
  try{r=app_control_set_app_id(c,id);if(r==0)r=app_control_set_operation(c,"http://tizen.org/appcontrol/operation/default");
   if(r==0&&id=="org.tizen.menu"){
    if(menuItem!=null){
     r=app_control_add_extra_data(c,"menuitem",menuItem);
     if(r==0)r=app_control_add_extra_data(c,"launchoption","pressed");
    }
    if(r==0)r=app_control_add_extra_data(c,"__K_EX_FORCE_BOOST","enable");
    if(r==0)r=app_control_add_extra_data(c,"__K_SPLASH_SCREEN","LA_UI_VR_TRANSPARENT");
   }
   if(r==0)r=app_control_send_launch_request(c,IntPtr.Zero,IntPtr.Zero);WriteState("launch:"+id+(menuItem==null?"":":"+menuItem)+":"+r);if(r!=0)ShowError("Could not open this screen. Try Advanced settings.");}finally{app_control_destroy(c);}
 }"""
    new_launch_method = """ bool TryManagedLaunch(string targetId,string menuItem)
 {
  try{
   var ac=new Tizen.Applications.AppControl();
   ac.ApplicationId=targetId;
   ac.Operation="http://tizen.org/appcontrol/operation/default";
   if(targetId=="org.tizen.menu"){
    if(menuItem!=null){
     ac.ExtraData.Add("menuitem",menuItem);
     ac.ExtraData.Add("launchoption","pressed");
    }
    ac.ExtraData.Add("__K_EX_FORCE_BOOST","enable");
    ac.ExtraData.Add("__K_SPLASH_SCREEN","LA_UI_VR_TRANSPARENT");
   }
   Tizen.Applications.AppControl.SendLaunchRequest(ac);
   return true;
  }catch{return false;}
 }
 void Launch(string id,string menuItem=null)
 {
  isPaused=true;
  if(TryManagedLaunch(id,menuItem)){WriteState("launch:"+id+(menuItem==null?"":":"+menuItem)+":0");return;}
  if(id=="9Ur5IzDKqV.TizenYouTube"&&TryManagedLaunch("com.samsung.tv.cobalt-yt",menuItem)){WriteState("launch:com.samsung.tv.cobalt-yt:0");return;}
  IntPtr c;int r=-1;
  try{r=app_control_create(out c);}catch(Exception ex){ShowError("Could not open app: "+ex.Message);return;}
  if(r!=0){ShowError("Could not open the app.");return;}
  try{r=app_control_set_app_id(c,id);if(r==0)r=app_control_set_operation(c,"http://tizen.org/appcontrol/operation/default");
   if(r==0&&id=="org.tizen.menu"){
    if(menuItem!=null){
     r=app_control_add_extra_data(c,"menuitem",menuItem);
     if(r==0)r=app_control_add_extra_data(c,"launchoption","pressed");
    }
    if(r==0)r=app_control_add_extra_data(c,"__K_EX_FORCE_BOOST","enable");
    if(r==0)r=app_control_add_extra_data(c,"__K_SPLASH_SCREEN","LA_UI_VR_TRANSPARENT");
   }
   if(r==0)r=app_control_send_launch_request(c,IntPtr.Zero,IntPtr.Zero);
   if(r!=0&&id=="9Ur5IzDKqV.TizenYouTube"){app_control_set_app_id(c,"com.samsung.tv.cobalt-yt");r=app_control_send_launch_request(c,IntPtr.Zero,IntPtr.Zero);}
   WriteState("launch:"+id+(menuItem==null?"":":"+menuItem)+":"+r);if(r!=0)ShowError("Could not open this screen. Try Advanced settings.");}finally{try{app_control_destroy(c);}catch{}}
 }"""
    src = src.replace(old_launch_method, new_launch_method)

    src = src.replace(
        '+"\\nmute="+currentMute+',
        '+"\\nmute="+currentMute+"\\nvoice="+currentVoice+"\\nspeaker="+currentSpeaker+"\\nsoundoutput_val="+SettingValue("soundoutput")+"\\nsoundoutput_name="+SettingName("soundoutput")+',
    )
    src = src.replace('File.WriteAllText(StateFile,', 'string statePayload=')
    src = src.replace(
        '+"\\nsleeptimer="+SettingValue("sleeptimer")+"\\n");',
        '+"\\nsleeptimer="+SettingValue("sleeptimer")+"\\n";'
        'try{File.WriteAllText("/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-state.txt",statePayload);}catch{}'
        'try{File.WriteAllText(StateFile,statePayload);}catch{}'
        'try{File.WriteAllText("/home/owner/share/tmp/sdk_tools/quiet-home-state.txt",statePayload);}catch{}',
    )

    src = src.replace(
        ' public static void Main(string[] args){using(var app=new QuietHome())app.Run(args);}\n}',
        ' [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]\n'
        ' public static void RunApp(string[] args){using(var app=new QuietHome())app.Run(args);}\n'
        '}\n'
        'public static class Program {\n'
        ' static void LogBoot(string msg){\n'
        '  try{File.AppendAllText("/opt/usr/home/owner/apps_rw/org.quiettizen.home/data/quiet-home-boot.txt",msg+"\\n");}catch{}\n'
        '  try{File.AppendAllText("/tmp/quiet-home-boot.txt",msg+"\\n");}catch{}\n'
        '  try{File.AppendAllText("/home/owner/share/tmp/sdk_tools/quiet-home-boot.txt",msg+"\\n");}catch{}\n'
        ' }\n'
        ' public static int Main(string[] args){\n'
        '  LogBoot("main_enter args="+string.Join(" ",args));\n'
        '  try{QuietHome.RunApp(args);LogBoot("main_exit_ok");return 0;}\n'
        '  catch(Exception ex){LogBoot("main_ex: "+ex.ToString());return 1;}\n'
        ' }\n'
        '}',
    )

    src = src.replace("Window.Default", "Tizen.NUI.Window.Instance")
    src = src.replace("clockTimer?.Start()", "if(clockTimer!=null)clockTimer.Start()")
    src = src.replace("clockTimer?.Stop()", "if(clockTimer!=null)clockTimer.Stop()")
    src = src.replace(
        "Math.Clamp(libraryPage,0,AppLibrary.PageCount(library.Count)-1)",
        "Math.Max(0,Math.Min(libraryPage,AppLibrary.PageCount(library.Count)-1))",
    )
    src = src.replace(
        "if(artworkCache.TryGetValue(key,out var cached))return cached;",
        "CachedArtwork cached;if(artworkCache.TryGetValue(key,out cached))return cached;",
    )
    src = src.replace("Environment.TickCount64", "(long)Environment.TickCount")
    src = src.replace(
        '[DllImport("libsettings-api.so")] static extern bool CSharpGetItemValue(string id,out string name,out string value);',
        '[DllImport("libsettings-api.so")] static extern bool CSharpGetItemValue(string id,out IntPtr name,out IntPtr value);',
    )
    src = src.replace(
        "try{if(CSharpGetItemValue(id,out var name,out var value)&&!string.IsNullOrEmpty(value)){settingValues[id]=value;settingNames[id]=name;}",
        "IntPtr p_name=IntPtr.Zero,p_val=IntPtr.Zero;bool s_en;try{if(CSharpGetItemValue(id,out p_name,out p_val)&&p_val!=IntPtr.Zero){string s_name=p_name!=IntPtr.Zero?Marshal.PtrToStringAnsi(p_name):\"\";string s_val=Marshal.PtrToStringAnsi(p_val);if(!string.IsNullOrEmpty(s_val)){settingValues[id]=s_val;settingNames[id]=s_name;}}",
    )
    src = src.replace("CSharpGetItemEnable(id,out var enabled)&&enabled", "CSharpGetItemEnable(id,out s_en)&&s_en")
    src = src.replace(
        'string SettingValue(string id){return settingValues.TryGetValue(id,out var v)?v:"";}',
        'string SettingValue(string id){string v;return settingValues.TryGetValue(id,out v)?v:"";}',
    )
    src = src.replace(
        'string SettingName(string id){return settingNames.TryGetValue(id,out var v)?v:"Unavailable";}',
        'string SettingName(string id){string v;return settingNames.TryGetValue(id,out v)?v:"Unavailable";}',
    )
    src = src.replace(
        "bool CanEdit(string id){return settingEnabled.TryGetValue(id,out var enabled)&&enabled&&settingValues.ContainsKey(id);}",
        "bool CanEdit(string id){bool enabled;return settingEnabled.TryGetValue(id,out enabled)&&enabled&&settingValues.ContainsKey(id);}",
    )
    src = src.replace(",CornerRadius=new Vector4(radius,radius,radius,radius)", "")
    src = src.replace("SamplingMode=SamplingModeType.BoxThenLanczos,\n", "")
    src = src.replace("SamplingMode=SamplingModeType.BoxThenLanczos,\r\n", "")
    src = src.replace("ReleasePolicy=ReleasePolicyType.Destroyed,CornerRadius=new Vector4(18,18,18,18)", "")
    src = src.replace(";tabs[i].CornerRadius=new Vector4(34,34,34,34)", "")
    src = src.replace("s.Card.BorderlineWidth=page==1&&s.Row>=0?(f?4:1):s.Row==0?1:0;\n", "")
    src = src.replace("s.Card.BorderlineWidth=page==1&&s.Row>=0?(f?4:1):s.Row==0?1:0;\r\n", "")
    src = src.replace("s.Card.BorderlineColor=page==1&&f?accent:new Color(1,1,1,f?.8f:.28f);\n", "")
    src = src.replace("s.Card.BorderlineColor=page==1&&f?accent:new Color(1,1,1,f?.8f:.28f);\r\n", "")

    (LOCAL / "HomeQ90T.cs").write_text(src, encoding="utf-8")

    # 3. Compile QuietHome.dll and strong-name whitelist stub DLLs
    refs = [f"/r:{p}" for p in sorted(fw.glob("*.dll")) if "DeveloperVer" not in p.name]
    cmd = [
        csc,
        "/noconfig",
        "/nostdlib",
        "/nologo",
        "/target:exe",
        str(f"/out:{BUILD / 'QuietHome.dll'}"),
        *refs,
        str(LOCAL / "AppLibraryQ90T.cs"),
        str(LOCAL / "HomeQ90T.cs"),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout, res.stderr)
    res.check_returncode()

    stub_cs = BUILD / "Stub.cs"
    stub_cs.write_text("namespace Stub { public static class Marker {} }\n", encoding="utf-8")
    stub_names = (
        "libsource-api.dll",
        "libvconf.dll",
        "libcapi-media-sound-manager-tv.dll",
        "libsettings-api.dll",
        "libcapi-appfw-app-control.dll",
    )
    for stub_name in stub_names:
        subprocess.run(
            [
                csc,
                "/noconfig",
                "/nostdlib",
                "/nologo",
                "/target:library",
                str(f"/out:{BUILD / stub_name}"),
                *refs,
                str(stub_cs),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    # 4. Assemble TPK directory layout
    if TPK_ROOT.exists():
        shutil.rmtree(TPK_ROOT)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    LIB_DIR.mkdir(parents=True, exist_ok=True)
    RES_DIR.mkdir(parents=True, exist_ok=True)
    SHARED_RES_DIR = TPK_ROOT / "shared" / "res"
    SHARED_RES_DIR.mkdir(parents=True, exist_ok=True)

    shutil.copy2(BUILD / "QuietHome.dll", BIN_DIR / "QuietHome.dll")
    for stub_name in stub_names:
        shutil.copy2(BUILD / stub_name, LIB_DIR / stub_name)
        shutil.copy2(BUILD / stub_name, BIN_DIR / stub_name)

    runtimeconfig = {
        "runtimeOptions": {
            "tfm": "netcoreapp2.0",
            "framework": {"name": "Microsoft.NETCore.App", "version": "2.0.0"},
        }
    }
    (BIN_DIR / "QuietHome.runtimeconfig.json").write_text(
        json.dumps(runtimeconfig, indent=2) + "\n", encoding="utf-8"
    )
    deps_json = {
        "runtimeTarget": {"name": ".NETCoreApp,Version=v2.0", "signature": ""},
        "compilationOptions": {},
        "targets": {".NETCoreApp,Version=v2.0": {"QuietHome/1.0.0": {"runtime": {"QuietHome.dll": {}}}}},
        "libraries": {"QuietHome/1.0.0": {"type": "project", "serviceable": False, "sha512": ""}},
    }
    (TPK_ROOT / "QuietHome.deps.json").write_text(json.dumps(deps_json, indent=2) + "\n", encoding="utf-8")
    (BIN_DIR / "QuietHome.deps.json").write_text(json.dumps(deps_json, indent=2) + "\n", encoding="utf-8")

    assets_src = ROOT / "launcher" / "assets"
    for item in assets_src.rglob("*"):
        if item.is_file():
            rel = item.relative_to(assets_src)
            dest = RES_DIR / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, dest)
    shutil.copy2(apps_local_path, RES_DIR / "apps.json")

    (RES_DIR / "app-icons").mkdir(parents=True, exist_ok=True)
    (RES_DIR / "app-icons" / "youtube-card.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#FF1E1E"/><stop offset="1" stop-color="#B80000"/></linearGradient></defs>'
        '<rect width="640" height="360" rx="28" fill="url(#bg)"/>'
        '<circle cx="560" cy="40" r="210" fill="#ffffff" opacity=".08"/>'
        '<rect x="210" y="102" width="220" height="156" rx="38" fill="#ffffff"/>'
        '<polygon points="295,142 295,218 365,180" fill="#E60000"/>'
        '</svg>',
        encoding="utf-8",
    )
    (RES_DIR / "feature-pc.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="442" viewBox="0 0 1020 430" preserveAspectRatio="none">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#14456B"/><stop offset=".52" stop-color="#1E6091"/><stop offset="1" stop-color="#2A9D8F"/></linearGradient>'
        '<linearGradient id="scr" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#E0FBFC"/><stop offset="1" stop-color="#98C1D9"/></linearGradient>'
        '<clipPath id="c"><rect width="1020" height="430" rx="18"/></clipPath></defs>'
        '<g clip-path="url(#c)"><rect width="1020" height="430" fill="url(#bg)"/>'
        '<circle cx="900" cy="70" r="260" fill="#A8DADC" opacity=".18"/>'
        '<circle cx="850" cy="150" r="195" fill="none" stroke="#E0FBFC" stroke-width="2" opacity=".3"/>'
        '<ellipse cx="775" cy="360" rx="190" ry="26" fill="#0B253A" opacity=".38"/>'
        '<g transform="translate(565 65)">'
        '<rect x="0" y="0" width="380" height="230" rx="18" fill="#1D2D44" stroke="#E0FBFC" stroke-width="6"/>'
        '<rect x="16" y="16" width="348" height="190" rx="8" fill="url(#scr)"/>'
        '<rect x="36" y="36" width="140" height="90" rx="6" fill="#3D5A80" opacity=".85"/>'
        '<rect x="192" y="36" width="150" height="40" rx="6" fill="#293241" opacity=".75"/>'
        '<rect x="192" y="88" width="150" height="82" rx="6" fill="#5C80BC" opacity=".65"/>'
        '<rect x="165" y="230" width="50" height="42" fill="#B8C5D6"/>'
        '<rect x="115" y="268" width="150" height="16" rx="8" fill="#E0FBFC"/>'
        '</g></g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "feature-consoles.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="442" viewBox="0 0 330 430" preserveAspectRatio="none">'
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#1656d9"/><stop offset=".52" stop-color="#3d36bc"/><stop offset="1" stop-color="#a856d6"/></linearGradient>'
        '<linearGradient id="pad" y2="1"><stop stop-color="#fff"/><stop offset="1" stop-color="#bcccef"/></linearGradient>'
        '<clipPath id="c"><rect width="330" height="430" rx="18"/></clipPath></defs>'
        '<g clip-path="url(#c)"><rect width="330" height="430" fill="url(#bg)"/>'
        '<circle cx="290" cy="40" r="145" fill="#7d80f8" opacity=".28"/>'
        '<g transform="translate(22 92) scale(0.65) rotate(-10 220 190)">'
        '<path d="M133 111C76 88 48 114 27 235C17 299 64 316 107 265L145 225H296L336 266C380 318 425 295 415 234C396 120 367 89 309 111Z" fill="url(#pad)"/>'
        '<path d="M148 119H294L282 187H160Z" fill="#b5c8e8"/>'
        '<path d="M153 210Q222 170 290 210L298 246H145Z" fill="#152249"/>'
        '<circle cx="159" cy="232" r="24" fill="#0f1b3d"/><circle cx="284" cy="232" r="24" fill="#0f1b3d"/>'
        '<path d="M95 143V189M72 166H118" stroke="#344563" stroke-width="13" stroke-linecap="round"/>'
        '<g fill="#586580"><circle cx="339" cy="142" r="9"/><circle cx="362" cy="165" r="9"/><circle cx="339" cy="188" r="9"/><circle cx="316" cy="165" r="9"/></g>'
        '</g></g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "quick-voice.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="410" height="286" viewBox="0 0 410 286">'
        '<defs><linearGradient id="b" x2="1" y2="1"><stop stop-color="#5A67D8"/><stop offset="1" stop-color="#313B8B"/></linearGradient></defs>'
        '<rect width="410" height="286" rx="24" fill="url(#b)"/>'
        '<circle cx="386" cy="18" r="138" fill="#ffffff" opacity=".08"/>'
        '<g transform="translate(310 66)" fill="none" stroke="#ffffff" stroke-width="4" stroke-linecap="round" opacity=".88">'
        '<rect x="18" y="6" width="20" height="34" rx="10"/>'
        '<path d="M10 26a18 18 0 0 0 36 0M28 44v12M18 56h20"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-pc.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="0" y2="1"><stop stop-color="#1E6091"/><stop offset="1" stop-color="#14456B"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<rect x="86" y="24" width="81" height="52" rx="6" fill="none" stroke="#fff" stroke-width="5"/>'
        '<rect x="118" y="78" width="17" height="12" fill="#fff"/>'
        '<rect x="102" y="90" width="49" height="6" rx="3" fill="#fff"/>'
        '</svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-consoles.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="0" y2="1"><stop stop-color="#4264d2"/><stop offset="1" stop-color="#172850"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<g transform="translate(76 26) scale(1.4)" fill="none" stroke="#fff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M20 14h32c11 0 18 33 11 38-6 4-14-10-20-10H29c-6 0-14 14-20 10-7-5 0-38 11-38z"/>'
        '<path d="M22 24v14m-7-7h14m19-3h1m6 6h1"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-chromecast.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="0" y2="1"><stop stop-color="#2A9D8F"/><stop offset="1" stop-color="#126d88"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<g transform="translate(82 28)" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round">'
        '<rect x="6" y="6" width="76" height="54" rx="8"/>'
        '<path d="M14 52a12 12 0 0 1 12 12M14 40a24 24 0 0 1 24 24M14 28a36 36 0 0 1 36 36"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-voice.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="0" y2="1"><stop stop-color="#5A67D8"/><stop offset="1" stop-color="#313B8B"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<g transform="translate(98 22)" fill="none" stroke="#fff" stroke-width="4.5" stroke-linecap="round">'
        '<rect x="18" y="6" width="20" height="36" rx="10"/>'
        '<path d="M8 28a20 20 0 0 0 40 0M28 48v14M16 62h24"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-settings.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="0" y2="1"><stop stop-color="#4A5568"/><stop offset="1" stop-color="#2D3748"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<g transform="translate(88 26)" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round">'
        '<line x1="8" y1="16" x2="68" y2="16"/><circle cx="26" cy="16" r="7" fill="#2D3748"/>'
        '<line x1="8" y1="38" x2="68" y2="38"/><circle cx="50" cy="38" r="7" fill="#2D3748"/>'
        '<line x1="8" y1="60" x2="68" y2="60"/><circle cx="34" cy="60" r="7" fill="#2D3748"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "free-dock-sound.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="253" height="126" viewBox="0 0 253 126">'
        '<defs><linearGradient id="b" x2="1" y2="1"><stop stop-color="#0F766E"/><stop offset="1" stop-color="#115E59"/></linearGradient></defs>'
        '<rect width="253" height="126" rx="22" fill="url(#b)"/>'
        '<circle cx="230" cy="24" r="72" fill="#ffffff" opacity=".08"/>'
        '<g transform="translate(182 32)" fill="none" stroke="#ffffff" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" opacity=".32">'
        '<polygon points="6,22 16,22 28,10 28,50 16,38 6,38" fill="#ffffff"/>'
        '<path d="M36 20a14 14 0 0 1 0 20M44 13a24 24 0 0 1 0 34"/>'
        '</g></svg>',
        encoding="utf-8",
    )

    def make_focus_svg(w: int, h: int, rx: int) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="3" y="3" width="{w-6}" height="{h-6}" rx="{rx}" fill="none" stroke="#38BDF8" stroke-width="6"/>'
            f'<rect x="7" y="7" width="{w-14}" height="{h-14}" rx="{max(4, rx-4)}" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-opacity=".95"/>'
            '</svg>'
        )

    (RES_DIR / "focus-hero.svg").write_text(make_focus_svg(1040, 442, 18), encoding="utf-8")
    (RES_DIR / "focus-portrait.svg").write_text(make_focus_svg(320, 442, 18), encoding="utf-8")
    (RES_DIR / "focus-dock.svg").write_text(make_focus_svg(253, 126, 22), encoding="utf-8")
    (RES_DIR / "focus-tile.svg").write_text(make_focus_svg(410, 286, 24), encoding="utf-8")
    (RES_DIR / "focus-app.svg").write_text(make_focus_svg(328, 184, 18), encoding="utf-8")
    (RES_DIR / "focus-toolbar.svg").write_text(make_focus_svg(68, 68, 34), encoding="utf-8")

    (RES_DIR / "free-background-dark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">'
        '<defs>'
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#0B0E14"/><stop offset=".5" stop-color="#111726"/><stop offset="1" stop-color="#0D111A"/>'
        '</linearGradient>'
        '<radialGradient id="g1" cx=".2" cy=".15" r=".55">'
        '<stop offset="0" stop-color="#1E3A8A" stop-opacity=".22"/><stop offset="1" stop-color="#0B0E14" stop-opacity="0"/>'
        '</radialGradient>'
        '<radialGradient id="g2" cx=".85" cy=".8" r=".5">'
        '<stop offset="0" stop-color="#0F766E" stop-opacity=".16"/><stop offset="1" stop-color="#0D111A" stop-opacity="0"/>'
        '</radialGradient>'
        '</defs>'
        '<rect width="1920" height="1080" fill="url(#bg)"/>'
        '<rect width="1920" height="1080" fill="url(#g1)"/>'
        '<rect width="1920" height="1080" fill="url(#g2)"/>'
        '</svg>',
        encoding="utf-8",
    )
    (RES_DIR / "glass-shelf-dark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="280" viewBox="0 0 1920 280">'
        '<defs><linearGradient id="s" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#182032" stop-opacity=".88"/><stop offset="1" stop-color="#0F1420" stop-opacity=".94"/>'
        '</linearGradient></defs>'
        '<rect x="44" y="38" width="1832" height="176" rx="36" fill="url(#s)" stroke="#2E3B59" stroke-width="1.5" stroke-opacity=".75"/>'
        '</svg>',
        encoding="utf-8",
    )
    (RES_DIR / "glass-button-dark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="112" viewBox="0 0 100 112">'
        '<circle cx="50" cy="54" r="36" fill="#05070B" opacity=".45"/>'
        '<circle cx="50" cy="50" r="34" fill="#1C2436" stroke="#334155" stroke-width="1.5"/>'
        '</svg>',
        encoding="utf-8",
    )
    (RES_DIR / "symbol-theme-dark.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">'
        '<g fill="none" stroke="#F1F5F9" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="15" cy="15" r="5.5"/>'
        '<path d="M15 3v3M15 24v3M3 15h3M24 15h3M6.5 6.5l2.1 2.1M21.4 21.4l2.1 2.1M23.5 6.5l-2.1 2.1M8.6 21.4l-2.1 2.1"/>'
        '</g></svg>',
        encoding="utf-8",
    )
    (RES_DIR / "symbol-theme-light.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" viewBox="0 0 30 30">'
        '<path d="M21.5 18.2A8.5 8.5 0 0 1 11.8 8.5a8.5 8.5 0 1 0 9.7 9.7z" fill="none" stroke="#1D1D1F" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>',
        encoding="utf-8",
    )

    icon_cs = BUILD / "MakeIcon.cs"
    icon_cs.write_text(
        """using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;

class MakeIcon {
    static void Main(string[] args) {
        using (var bmp = new Bitmap(512, 512))
        using (var g = Graphics.FromImage(bmp)) {
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.TextRenderingHint = TextRenderingHint.AntiAliasGridFit;
            var rect = new Rectangle(0, 0, 512, 512);
            using (var bg = new LinearGradientBrush(rect, Color.FromArgb(255, 13, 19, 33), Color.FromArgb(255, 24, 38, 64), 45f)) {
                g.FillRectangle(bg, rect);
            }
            using (var glowPen = new Pen(Color.FromArgb(140, 56, 189, 248), 8f)) {
                g.DrawRectangle(glowPen, 16, 16, 480, 480);
            }
            using (var sf = new StringFormat { Alignment = StringAlignment.Center, LineAlignment = StringAlignment.Center })
            using (var f1 = new Font("Segoe UI", 86f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var f2 = new Font("Segoe UI", 86f, FontStyle.Bold, GraphicsUnit.Pixel))
            using (var b1 = new SolidBrush(Color.FromArgb(255, 241, 245, 249)))
            using (var b2 = new SolidBrush(Color.FromArgb(255, 96, 165, 250))) {
                g.DrawString("QUIET", f1, b1, new RectangleF(0, 118, 512, 130), sf);
                g.DrawString("TIZEN", f2, b2, new RectangleF(0, 248, 512, 130), sf);
            }
            bmp.Save(args[0], System.Drawing.Imaging.ImageFormat.Png);
        }
    }
}
""",
        encoding="utf-8",
    )
    icon_exe = BUILD / "MakeIcon.exe"
    subprocess.run([csc, "/nologo", f"/out:{icon_exe}", str(icon_cs)], check=True, capture_output=True, text=True)
    icon_png = BUILD / "quiet-tizen-icon.png"
    subprocess.run([str(icon_exe), str(icon_png)], check=True, capture_output=True, text=True)
    shutil.copy2(icon_png, SHARED_RES_DIR / "quiet-tizen-icon.png")
    shutil.copy2(icon_png, RES_DIR / "quiet-tizen-icon.png")

    manifest = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns="http://tizen.org/ns/packages" api-version="5.0" package="org.quiettizen.home" version="1.0.0">
  <profile name="tv" />
  <ui-application appid="org.quiettizen.home" exec="QuietHome.dll" type="dotnet" multiple="false" taskmanage="true" nodisplay="false" splash-screen-display="false" launch_mode="single">
    <label>Quiet Tizen</label>
    <icon>quiet-tizen-icon.png</icon>
  </ui-application>
  <privileges>
    <privilege>http://tizen.org/privilege/appmanager.launch</privilege>
    <privilege>http://tizen.org/privilege/window.priority.set</privilege>
  </privileges>
  <feature name="http://tizen.org/feature/screen.size.normal.1080.1920">true</feature>
</manifest>
"""
    (TPK_ROOT / "tizen-manifest.xml").write_text(manifest, encoding="utf-8")

    unsigned_tpk = BUILD / "org.quiettizen.home-1.0.0-unsigned.tpk"
    if unsigned_tpk.exists():
        unsigned_tpk.unlink()
    all_files = [f for f in TPK_ROOT.rglob("*") if f.is_file()]
    all_files.sort(key=lambda f: (len(f.relative_to(TPK_ROOT).parts) == 1, f.relative_to(TPK_ROOT).as_posix()))
    with zipfile.ZipFile(unsigned_tpk, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in all_files:
            zf.write(f, f.relative_to(TPK_ROOT).as_posix())
    print("Created unsigned TPK:", unsigned_tpk.relative_to(ROOT), "size:", unsigned_tpk.stat().st_size)


if __name__ == "__main__":
    main()
