import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const WonderLoopApp());

class WonderLoopApp extends StatelessWidget {
  const WonderLoopApp({super.key});
  @override Widget build(BuildContext context) => MaterialApp(
    debugShowCheckedModeBanner:false, title:'WonderLoop v1.2',
    theme:ThemeData(useMaterial3:true,colorSchemeSeed:Colors.deepPurple), home:const HomePage());
}

class HomePage extends StatefulWidget { const HomePage({super.key}); @override State<HomePage> createState()=>_HomePageState(); }
class _HomePageState extends State<HomePage> {
  final prompt=TextEditingController();
  String length='1 minute', style='3D Cartoon', format='YouTube 16:9', visualMode='WonderLoop Illustrated', language='English';
  String? characterId, bibleId, videoUrl, jobId;
  String? projectTitle; List<dynamic> projects=[]; String creatorName='WonderLoop Creator'; bool generating=false; int progress=0; String status=''; List<dynamic> scenes=[]; int selectedScene=0;
  String baseUrl='http://127.0.0.1:8000';
  List<dynamic> characters=[], bibles=[];

  @override void initState(){super.initState(); _loadLibrary(); _loadProjects(); _loadProfile();}
  Future<void> _loadProfile() async { try { final r=await http.get(Uri.parse('$baseUrl/api/profile')); if(r.statusCode==200 && mounted){final d=jsonDecode(r.body); setState((){creatorName=d['name']??'WonderLoop Creator'; language=d['language']??language;});}} catch(_){ } }

Future<void> _showHealth() async { try { final r=await http.get(Uri.parse('$baseUrl/api/health')); if(!mounted)return; final d=jsonDecode(r.body); showDialog(context:context,builder:(ctx)=>AlertDialog(title:const Text('WonderLoop system health'),content:Column(mainAxisSize:MainAxisSize.min,crossAxisAlignment:CrossAxisAlignment.start,children:[Text('API: ${d['status']??'unknown'}'),Text('FFmpeg: ${d['ffmpeg']==true?'Ready':'Missing'}'),Text('eSpeak: ${d['espeak']==true?'Ready':'Missing'}'),Text('Version: ${d['version']??'unknown'}')]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Close'))])); } catch(_) { if(mounted) _error('Could not reach the WonderLoop backend.'); } }

Future<void> _saveProfile() async { final name=TextEditingController(text:creatorName); final langs=['English','French','Spanish','Portuguese','German','Italian','Hindi','Arabic']; await showDialog(context:context,builder:(ctx)=>AlertDialog(title:const Text('Creator profile'),content:Column(mainAxisSize:MainAxisSize.min,children:[TextField(controller:name,decoration:const InputDecoration(labelText:'Creator name')),const SizedBox(height:12),DropdownButtonFormField<String>(value:language,items:langs.map((x)=>DropdownMenuItem(value:x,child:Text(x))).toList(),onChanged:(v){if(v!=null)setState(()=>language=v);},decoration:const InputDecoration(labelText:'Default language',border:OutlineInputBorder()))]),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancel')),FilledButton(onPressed:() async {await http.put(Uri.parse('$baseUrl/api/profile'),headers:{'Content-Type':'application/json'},body:jsonEncode({'id':'local-creator','name':name.text.trim().isEmpty?'WonderLoop Creator':name.text.trim(),'language':language}));if(mounted)setState(()=>creatorName=name.text.trim().isEmpty?'WonderLoop Creator':name.text.trim());if(ctx.mounted)Navigator.pop(ctx);},child:const Text('Save'))])); }

Future<void> _loadProjects() async { try { final r=await http.get(Uri.parse('$baseUrl/api/projects')); if(r.statusCode==200 && mounted)setState((){projects=jsonDecode(r.body);}); } catch(_){ } }

  void _usePrompt(String value){setState((){prompt.text=value; prompt.selection=TextSelection.collapsed(offset:prompt.text.length);});}

  Future<void> _loadLibrary() async { try { final c=await http.get(Uri.parse('$baseUrl/api/characters')); final b=await http.get(Uri.parse('$baseUrl/api/story-bibles')); if(mounted){setState((){characters=jsonDecode(c.body);bibles=jsonDecode(b.body);});}} catch(_){ } }

  Future<void> generate() async {
    if(prompt.text.trim().length<3) return;
    setState((){generating=true; progress=0; status='Sending your idea to WonderLoop…'; videoUrl=null;});
    try {
      final r=await http.post(Uri.parse('$baseUrl/api/generate'),headers:{'Content-Type':'application/json'},body:jsonEncode({'prompt':prompt.text.trim(),'length':length,'style':style,'format':format,'visual_mode':visualMode,'character_id':characterId,'bible_id':bibleId,'music':true,'narration':true,'captions':true,'language':language,'creator_id':'local-creator'}));
      if(r.statusCode<200||r.statusCode>=300) throw Exception(r.body);
      final data=jsonDecode(r.body); final id=data['job_id'];
      Timer.periodic(const Duration(seconds:1),(timer) async {
        try {
          final q=await http.get(Uri.parse('$baseUrl/api/jobs/$id')); final d=jsonDecode(q.body);
          if(!mounted){timer.cancel();return;}
          setState((){progress=(d['progress']??0); status=d['phase']??'Generating…';});
          if(d['status']=='completed'){timer.cancel();setState((){generating=false;status='Video ready!';jobId=id;videoUrl='$baseUrl${d['video_url']}';projectTitle=d['title']??'WonderLoop Project';});await _loadScenes(id);await _loadProjects();}
          else if(d['status']=='failed'){timer.cancel();setState((){generating=false;status='Generation failed';});_error(d['error']??'Unknown error');}
        } catch(_){timer.cancel();if(mounted){setState((){generating=false;});_error('Could not reach the WonderLoop backend.');}}
      });
    } catch(e){setState((){generating=false;});_error('Start the WonderLoop backend, then try again.');}
  }
  void _error(String text)=>showDialog(context:context,builder:(_)=>AlertDialog(title:const Text('Something went wrong'),content:Text(text),actions:[TextButton(onPressed:()=>Navigator.pop(context),child:const Text('OK'))]));

  Future<void> _loadScenes(String id) async {
    try { final r=await http.get(Uri.parse('$baseUrl/api/jobs/$id/scenes')); if(r.statusCode==200 && mounted){setState((){scenes=jsonDecode(r.body)['scenes']??[]; selectedScene=0;});} } catch(_){ }
  }
  Future<void> _saveScene(int index, String narration) async {
    if(jobId==null) return;
    await http.put(Uri.parse('$baseUrl/api/jobs/$jobId/scenes/${index+1}'),headers:{'Content-Type':'application/json'},body:jsonEncode({'narration':narration}));
    await _loadScenes(jobId!);
  }
  Future<void> _rebuildVideo() async {
    if(jobId==null) return;
    setState((){generating=true;progress=0;status='Rebuilding your edited video…';});
    try { final r=await http.post(Uri.parse('$baseUrl/api/jobs/$jobId/rebuild')); if(r.statusCode>=300) throw Exception(); final id=jsonDecode(r.body)['job_id']; Timer.periodic(const Duration(seconds:1),(timer) async {try{final q=await http.get(Uri.parse('$baseUrl/api/jobs/$id'));final d=jsonDecode(q.body);if(!mounted){timer.cancel();return;}setState((){progress=d['progress']??0;status=d['phase']??'Rebuilding…';});if(d['status']=='completed'){timer.cancel();setState((){generating=false;status='Edited video ready!';videoUrl='$baseUrl${d['video_url']}';});await _loadScenes(id);}else if(d['status']=='failed'){timer.cancel();setState((){generating=false;status='Rebuild failed';});}}catch(_){timer.cancel();if(mounted)setState((){generating=false;});}}); } catch(_){setState((){generating=false;});_error('Could not rebuild the video.');}
  }
  void _openEditor() {
    if(jobId==null || scenes.isEmpty) return;
    Navigator.push(context, MaterialPageRoute(builder:(_)=>EditorPage(baseUrl:baseUrl,jobId:jobId!,scenes:scenes,onSaved:(){_loadScenes(jobId!);},onRebuild:_rebuildVideo)));
  }

  Future<void> _addCharacter() async {
    final name=TextEditingController(), species=TextEditingController(text:'friendly animal'), personality=TextEditingController(text:'kind, playful and curious'), appearance=TextEditingController(text:'bright, colorful and child-friendly');
    await showDialog(context:context,builder:(ctx)=>AlertDialog(title:const Text('Create character'),content:SingleChildScrollView(child:Column(children:[TextField(controller:name,decoration:const InputDecoration(labelText:'Name')),TextField(controller:species,decoration:const InputDecoration(labelText:'Species')),TextField(controller:personality,decoration:const InputDecoration(labelText:'Personality')),TextField(controller:appearance,decoration:const InputDecoration(labelText:'Appearance'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancel')),FilledButton(onPressed:() async {if(name.text.trim().isEmpty)return; await http.post(Uri.parse('$baseUrl/api/characters'),headers:{'Content-Type':'application/json'},body:jsonEncode({'name':name.text,'species':species.text,'personality':personality.text,'appearance':appearance.text,'voice':'cheerful'})); if(ctx.mounted)Navigator.pop(ctx); await _loadLibrary();},child:const Text('Save'))]));
  }
  Future<void> _addBible() async {
    final title=TextEditingController(), world=TextEditingController(text:'A safe, colorful and imaginative world for children.'), rules=TextEditingController();
    await showDialog(context:context,builder:(ctx)=>AlertDialog(title:const Text('Create Story Bible'),content:SingleChildScrollView(child:Column(children:[TextField(controller:title,decoration:const InputDecoration(labelText:'Series title')),TextField(controller:world,maxLines:3,decoration:const InputDecoration(labelText:'World description')),TextField(controller:rules,maxLines:3,decoration:const InputDecoration(labelText:'Rules (one per line)'))])),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancel')),FilledButton(onPressed:() async {if(title.text.trim().isEmpty)return; await http.post(Uri.parse('$baseUrl/api/story-bibles'),headers:{'Content-Type':'application/json'},body:jsonEncode({'title':title.text,'world':world.text,'rules':rules.text.split('\n').where((x)=>x.trim().isNotEmpty).toList(),'characters':characters.map((x)=>x['id']).toList()})); if(ctx.mounted)Navigator.pop(ctx); await _loadLibrary();},child:const Text('Save'))]));
  }

  @override Widget build(BuildContext context){
    final prompts=[
      'Make a fun song teaching children to eat fruits.',
      'Create a playful story that teaches children to count from 1 to 10.',
      'Make a cheerful alphabet adventure with friendly animals.',
      'Create a bedtime story about a little elephant learning to share.'
    ];
    return Scaffold(
      appBar:AppBar(title:const Row(children:[Text('✨ '),Text('WonderLoop',style:TextStyle(fontWeight:FontWeight.bold))]),actions:[
        TextButton.icon(onPressed:_addCharacter,icon:const Icon(Icons.face),label:const Text('Characters')),
        TextButton.icon(onPressed:_addBible,icon:const Icon(Icons.menu_book),label:const Text('Story Bible')), TextButton.icon(onPressed:_saveProfile,icon:const Icon(Icons.person),label:Text(creatorName)), TextButton.icon(onPressed:_showHealth,icon:const Icon(Icons.health_and_safety),label:const Text('Health'))]),
      body:Center(child:SingleChildScrollView(padding:const EdgeInsets.all(24),child:ConstrainedBox(constraints:const BoxConstraints(maxWidth:1050),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        const SizedBox(height:18),
        Text('Create your next kids video',style:Theme.of(context).textTheme.headlineLarge?.copyWith(fontWeight:FontWeight.bold)),
        const SizedBox(height:8),
        const Text('One idea in. WonderLoop plans, illustrates, narrates, captions and assembles a complete MP4.'),
        const SizedBox(height:20),
        Wrap(spacing:10,runSpacing:10,children:prompts.map((p)=>ActionChip(label:Text(p,maxLines:1,overflow:TextOverflow.ellipsis),onPressed:()=>_usePrompt(p))).toList()),
        const SizedBox(height:18),
        Card(child:Padding(padding:const EdgeInsets.all(20),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          const Text('1. Describe your video',style:TextStyle(fontWeight:FontWeight.bold,fontSize:18)),const SizedBox(height:10),
          TextField(controller:prompt,maxLines:5,decoration:const InputDecoration(hintText:'Example: Make a 3-minute sing-along teaching children why fruits are good for them.',border:OutlineInputBorder())),
          const SizedBox(height:18),
          const Text('2. Choose your output',style:TextStyle(fontWeight:FontWeight.bold,fontSize:18)),const SizedBox(height:10),
          Wrap(spacing:12,runSpacing:12,children:[drop('Length',length,['1 minute','3 minutes','5 minutes'],(v)=>setState(()=>length=v!)),drop('Animation',style,['2D Cartoon','3D Cartoon','Storybook'],(v)=>setState(()=>style=v!)),drop('Format',format,['YouTube 16:9','Shorts 9:16','Square 1:1'],(v)=>setState(()=>format=v!)),drop('Language',language,['English','French','Spanish','Portuguese','German','Italian','Hindi','Arabic'],(v)=>setState(()=>language=v!)),drop('Character',characterId,[null,...characters.map((x)=>x['id'] as String?)],(v)=>setState(()=>characterId=v)),drop('Story Bible',bibleId,[null,...bibles.map((x)=>x['id'] as String?)],(v)=>setState(()=>bibleId=v))]),
          const SizedBox(height:20),SizedBox(width:double.infinity,height:56,child:FilledButton.icon(onPressed:generating?null:generate,icon:generating?const SizedBox(width:20,height:20,child:CircularProgressIndicator(strokeWidth:2)):const Icon(Icons.auto_awesome),label:Text(generating?'CREATING $progress%':'CREATE VIDEO'))),
          if(generating||status.isNotEmpty)...[const SizedBox(height:16),LinearProgressIndicator(value:generating?progress/100:1),const SizedBox(height:8),Text(status)],
          if(videoUrl!=null&&!generating)...[const SizedBox(height:18),Card(color:Theme.of(context).colorScheme.surfaceContainerHighest,child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(projectTitle??'Your WonderLoop video',style:const TextStyle(fontWeight:FontWeight.bold,fontSize:18)),const SizedBox(height:8),const Text('Your video is ready. Open the MP4 or edit scenes before rebuilding.'),const SizedBox(height:12),Wrap(spacing:10,runSpacing:10,children:[FilledButton.icon(onPressed:()=>_openEditor(),icon:const Icon(Icons.edit),label:const Text('EDIT VIDEO')),OutlinedButton.icon(onPressed:()=>_usePrompt(''),icon:const Icon(Icons.add),label:const Text('CREATE ANOTHER'))])])))]
        ]))),
        const SizedBox(height:20),
        Row(children:[Text('Your projects',style:Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight:FontWeight.bold)),const Spacer(),TextButton.icon(onPressed:_loadProjects,icon:const Icon(Icons.refresh),label:const Text('Refresh'))]),
        if(projects.isEmpty) const Card(child:Padding(padding:EdgeInsets.all(18),child:Text('Your completed projects will appear here.'))),
        if(projects.isNotEmpty) ...projects.take(6).map((p)=>Card(child:ListTile(leading:const CircleAvatar(child:Icon(Icons.movie)),title:Text(p['title']??'Untitled'),subtitle:Text(p['status']??'queued'),trailing:PopupMenuButton<String>(onSelected:(v) async { if(v=='open' && p['video_url']!=null){setState((){jobId=p['job_id'];videoUrl='$baseUrl${p['video_url']}';projectTitle=p['title'];});_loadScenes(p['job_id']);} else if(v=='rename'){final c=TextEditingController(text:p['title']??''); await showDialog(context:context,builder:(ctx)=>AlertDialog(title:const Text('Rename project'),content:TextField(controller:c,decoration:const InputDecoration(labelText:'Project title')),actions:[TextButton(onPressed:()=>Navigator.pop(ctx),child:const Text('Cancel')),FilledButton(onPressed:() async {await http.put(Uri.parse('$baseUrl/api/projects/${p['job_id']}'),headers:{'Content-Type':'application/json'},body:jsonEncode({'title':c.text}));if(ctx.mounted)Navigator.pop(ctx);await _loadProjects();},child:const Text('Save'))]));} else if(v=='delete'){await http.delete(Uri.parse('$baseUrl/api/projects/${p['job_id']}'));await _loadProjects();}},itemBuilder:(_)=>const [PopupMenuItem(value:'open',child:Text('Open')),PopupMenuItem(value:'rename',child:Text('Rename')),PopupMenuItem(value:'delete',child:Text('Delete'))])))).toList(),
        const SizedBox(height:18),
        Wrap(spacing:14,runSpacing:14,children:const [Feature(i:'🧠',t:'One-prompt Copilot',x:'Turn an idea into a complete video plan'),Feature(i:'🧸',t:'Characters',x:'Reuse recurring characters'),Feature(i:'📖',t:'Story Bible',x:'Keep series worlds consistent'),Feature(i:'🎙️',t:'Voice + music',x:'Automatic local audio'),Feature(i:'✂️',t:'Scene editor',x:'Edit and rebuild without starting over')])
      ]))));
  }
  Widget drop(String label,String? value,List<String?> values,ValueChanged<String?> f)=>SizedBox(width:210,child:DropdownButtonFormField<String?>(value:value,decoration:InputDecoration(labelText:label,border:const OutlineInputBorder()),items:values.map((x)=>DropdownMenuItem<String?>(value:x,child:Text(x==null?'None':_displayName(x)))).toList(),onChanged:f));
  String _displayName(String id){for(final x in characters){if(x['id']==id)return x['name']??'Character';}for(final x in bibles){if(x['id']==id)return x['title']??'Story Bible';}return id;}
}
class Feature extends StatelessWidget{final String i,t,x;const Feature({super.key,required this.i,required this.t,required this.x});@override Widget build(BuildContext c)=>SizedBox(width:230,child:Card(child:Padding(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(i,style:const TextStyle(fontSize:28)),const SizedBox(height:6),Text(t,style:const TextStyle(fontWeight:FontWeight.bold)),Text(x)]))));}


class EditorPage extends StatefulWidget {
  final String baseUrl, jobId; final List<dynamic> scenes; final VoidCallback onSaved; final VoidCallback onRebuild;
  const EditorPage({super.key,required this.baseUrl,required this.jobId,required this.scenes,required this.onSaved,required this.onRebuild});
  @override State<EditorPage> createState()=>_EditorPageState();
}
class _EditorPageState extends State<EditorPage> {
  late List<dynamic> scenes; int selected=0; late TextEditingController narration;
  @override void initState(){super.initState();scenes=List<dynamic>.from(widget.scenes);narration=TextEditingController(text:scenes[0]['narration']??'');}
  void pick(int i){setState((){selected=i;narration.text=scenes[i]['narration']??'';});}
  Future<void> save(){return http.put(Uri.parse('${widget.baseUrl}/api/jobs/${widget.jobId}/scenes/${selected+1}'),headers:{'Content-Type':'application/json'},body:jsonEncode({'narration':narration.text})).then((_){scenes[selected]['narration']=narration.text;widget.onSaved();setState((){});});}
  @override Widget build(BuildContext context)=>Scaffold(appBar:AppBar(title:const Text('WonderLoop Editor'),actions:[TextButton.icon(onPressed:widget.onRebuild,icon:const Icon(Icons.movie),label:const Text('REBUILD VIDEO'))]),body:Row(children:[SizedBox(width:300,child:ListView.builder(itemCount:scenes.length,itemBuilder:(c,i)=>ListTile(selected:i==selected,leading:CircleAvatar(child:Text('${i+1}')),title:Text('Scene ${i+1}'),subtitle:Text(scenes[i]['narration']??'',maxLines:2,overflow:TextOverflow.ellipsis),onTap:()=>pick(i)))),Expanded(child:Padding(padding:const EdgeInsets.all(24),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text('Scene ${selected+1}',style:const TextStyle(fontSize:28,fontWeight:FontWeight.bold)),const SizedBox(height:16),Container(height:260,width:double.infinity,decoration:BoxDecoration(borderRadius:BorderRadius.circular(18),border:Border.all(color:Theme.of(context).colorScheme.outlineVariant)),child:Image.network('${widget.baseUrl}/api/jobs/${widget.jobId}/thumbnail',fit:BoxFit.cover,errorBuilder:(_,__,___)=>const Center(child:Icon(Icons.image,size:64)))),const SizedBox(height:18),TextField(controller:narration,maxLines:7,decoration:const InputDecoration(labelText:'Narration / captions',border:OutlineInputBorder())),const SizedBox(height:14),Row(children:[FilledButton.icon(onPressed:save,icon:const Icon(Icons.save),label:const Text('SAVE SCENE')),const SizedBox(width:10),Text('Changes are applied when you rebuild the video.')])])))]));
}
