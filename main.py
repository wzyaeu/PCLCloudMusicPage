from MusicLibrary.neteaseCloudMusicApi import NeteaseCloudMusicApi

import os
import shutil
import json
import secrets
import requests

def load_template(name, noxaml = False):
    print(f'load_template-加载模板文件-{name}')
    global templates
    if not name in templates:
        t_path = os.path.join(BASE_PATH, 'templates', name+('' if noxaml else '.xaml'))
        with open(t_path,'r', encoding='utf-8') as f:
            templates[name] =  f.read()

def save_output_file(name, data):
    print(f'save_output_file-保存输出文件-{name}')
    o_path = os.path.join(BASE_PATH, 'output', name)
    with open(o_path,'w', encoding='utf-8') as f:
        f.write(data)

def replaces(string: str, s: dict):
    output = string
    for l, d in s.items():
        output = output.replace('{'+l+'}', str(d))
    return output

def uninumber(n: int):
    if n >= 100000000:
        return '{:.1f}'.format(n/100000000) + '亿'
    elif n >= 10000:
        return '{:.1f}'.format(n/10000) + '万'
    else:
        return n
    
def nlv(s):
    return '\\n'.join(str(s).splitlines())

def escape_xaml(text):
    if text is None:
        return ''
    return (
        text.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace(''', '&quot;')
             .replace(''', '&apos;')
    )

def mainpage():
    print('mainpage-开始')
    print('mainpage-加载模板')
    load_template('mainpage')
    load_template('music')
    print('mainpage-获取api数据')
    music_data: dict = ncm.playlist_track_all(3779629).data # type: ignore
    music_list = music_data['songs'][:10]
    print('mainpage-构建页面')
    output = replaces(templates['mainpage'],{
        'music':'\n'.join([
            replaces(templates['music'],{
                'tag':'',
                'khd':'Visible',
                'khdtype':'song',
                'id':m['id'],
                'img': escape_xaml(m['al']['picUrl']),
                'name': escape_xaml(m['name']),
                'artists': escape_xaml('/'.join([
                    artist['name']
                    for artist in m['ar']
                ])),
                'url': escape_xaml(f'https://music.163.com/#/song?id={m['id']}'),
                'album': escape_xaml(m['al']['name']),
                '':print(f'mainpage-music-构建内容-{index}/{len(music_list)}')
            }) for index, m in enumerate(music_list,start=1)
        ]),
        'gv':BUILD_VERSION
    })
    print('mainpage-保存输出文件')
    save_output_file('Custom.xaml',output)
    save_output_file('Custom.xaml.ini',BUILD_VERSION)

def newsongpage():
    print('newsongpage-开始')
    print('newsongpage-加载模板')
    load_template('newsongpage')
    load_template('music')

    print(f'newsongpage-获取api数据')
    music_data: dict = ncm.top_song(0).data # type: ignore

    print('newsongpage-构建页面')
    output = replaces(templates['newsongpage'],{
        'music':'\n'.join([
            replaces(templates['music'],{
                'tag':'',
                'khd':'Visible',
                'khdtype':'song',
                'id':m['id'],
                'img': escape_xaml(m['album']['blurPicUrl']),
                'name': escape_xaml(m['name']),
                'artists': escape_xaml('/'.join([
                    artist['name']
                    for artist in m['artists']
                ])),
                'url': escape_xaml(f'https://music.163.com/#/song?id={m['id']}'),
                'album': escape_xaml(m['album']['name']),
                '':print(f'newsongpage-music-构建内容-{index}/{len(music_data['data'])}')
            }) for index, m in enumerate(music_data['data'],start=1)
        ])
    })
    print('newsongpage-保存输出文件')
    save_output_file(f'newsong.json',json.dumps(
        {
            'Title': f'Music 云音乐热门'
        }
    ,ensure_ascii=False))
    save_output_file(f'newsong.xaml',output)

def rankpage(listtype):
    print(f'rankpage-开始-{listtype['name']}-{listtype['id']}')
    print('rankpage-加载模板')
    load_template('music')
    load_template('rankpage')
    load_template('rankpage-next')
    load_template('rankpage-musictag')

    print(f'rankpage-获取api数据')
    music_data = rankncm.playlist_track_all(listtype['id'])
    music_list = music_data.data['songs']
    chunk_size = 20
    music_lists = [music_list[i:i + chunk_size] for i in range(0, len(music_list), chunk_size)] if len(music_list) > 0 else [[]]
    all_output = []
    print(f'rankpage-构建页面')
    for vlindex, vl in enumerate(music_lists, start=1):
        print(f'rankpage-构建页面-{vlindex}/{len(music_lists)}')
        output = replaces(templates['rankpage'],{
            'num':vlindex,
            'listname':escape_xaml(listtype['name']),
            'total':len(music_lists),
            'music':'\n'.join([
                replaces(templates['music'],{
                    'khd':'Visible',
                    'khdtype':'song',
                    'id':m['id'],
                    'img': escape_xaml(m['al']['picUrl']),
                    'name': escape_xaml(m['name']),
                    'artists': escape_xaml('/'.join([
                        artist['name']
                        for artist in m['ar']
                    ])),
                    'url': escape_xaml(f'https://music.163.com/#/song?id={m['id']}'),
                    'album': escape_xaml(m['al']['name']),
                    'tag':replaces(templates['rankpage-musictag'],{
                        'color': '#ffbe35' if index == 1 else(
                        '#99bce0' if index == 2 else(
                        '#f5b7a3' if index == 3 else
                        '#7b859a')),
                        'rank': index,
                    }),
                }) for index, m in enumerate(vl,start=1+(vlindex-1)*20)
            ]),
            'next': '' if vlindex == len(music_lists) else replaces(templates['rankpage-next'],{
                'num':vlindex+1,
                'ltype':listtype['id']
            }),
        })

        all_output.append(output)
    print('rankpage-保存输出文件')
    for index, o in enumerate(all_output, start=1):
        print(f'rankpage-保存输出文件-{index}/{len(music_lists)}')
        save_output_file(f'{listtype['id']}_rank_{index}.json',json.dumps(
            {
                'Title': f'Music 云音乐 {listtype['name']} | 第 {index} / {len(music_lists)} 页'
            }
        ,ensure_ascii=False))
        save_output_file(f'{listtype['id']}_rank_{index}.xaml',o)

def ranklistpage(rank_l):
    print('ranklistpage-开始')
    print('ranklistpage-加载模板')
    load_template('ranklistpage')
    load_template('ranklistpage-item')
    output = ''
    for index, listtype in enumerate(rank_l, start=1):
        print(f'ranklistpage-添加排行榜-{listtype['name']}')
        output += replaces(templates['ranklistpage-item'],{
            'name':escape_xaml(listtype['name']),
            'description':(lambda x: f'#{index}' if x == '' else x)(escape_xaml(listtype['description'])),
            'mrank':listtype['id'],
            'num':index
        })
    output = replaces(templates['ranklistpage'],{
        'item':output,
    })
    print('ranklistpage-保存输出文件')
    save_output_file(f'rank_list.json',json.dumps(
        {
            'Title': f'热门榜单'
        }
    ,ensure_ascii=False))
    save_output_file(f'rank_list.xaml',output)

def highqualitylistpage():
    print('highqualitylistpage-开始')
    print('highqualitylistpage-加载模板')
    load_template('highqualitylistpage')
    load_template('music')

    print(f'highqualitylistpage-获取api数据')
    music_data = ncm.top_playlist_highquality().data['playlists']

    print('highqualitylistpage-构建页面')
    output = replaces(templates['highqualitylistpage'],{
        'item':'\n'.join([
            replaces(templates['music'],{
                'tag':'',
                'khd':'Visible',
                'khdtype':'playlist',
                'id':l['id'],
                'img': escape_xaml(l['coverImgUrl']),
                'name': escape_xaml(l['name']),
                'artists': escape_xaml(l['creator']['nickname']),
                'url': escape_xaml(f'https://music.163.com/#/playlist?id={l['id']}'),
                'album': f'包含{l['trackCount']}首歌',
                '':print(f'highqualitylistpage-playlist-构建内容-{index}/{len(music_data)}')
            }) for index, l in enumerate(music_data,start=1)
        ])
    })

    print('highqualitylistpage-保存输出文件')
    save_output_file(f'highqualitylist.json',json.dumps(
        {
            'Title': f'精品歌单'
        }
    ,ensure_ascii=False))
    save_output_file(f'highqualitylist.xaml',output)

def newalbum():
    print('newalbum-开始')
    print('newalbum-加载模板')
    load_template('newalbum')
    load_template('music')

    print(f'newalbum-获取api数据')
    music_data = ncm.album_new().data['albums']

    print('newalbum-构建页面')
    output = replaces(templates['newalbum'],{
        'item':'\n'.join([
            replaces(templates['music'],{
                'khd':'Visible',
                'khdtype':'album',
                'id':l['id'],
                'tag':'',
                'img': escape_xaml(l['picUrl']),
                'name': escape_xaml(l['name']),
                'artists': escape_xaml('/'.join([
                    artist['name']
                    for artist in l['artists']
                ])),
                'url': escape_xaml(f'https://music.163.com/#/album?id={l['id']}'),
                'album': f'包含{l['size']}首歌',
                '':print(f'newalbum-playlist-构建内容-{index}/{len(music_data)}')
            }) for index, l in enumerate(music_data,start=1)
        ])
    })

    print('newalbum-保存输出文件')
    save_output_file(f'newalbum.json',json.dumps(
        {
            'Title': f'新碟上架'
        }
    ,ensure_ascii=False))
    save_output_file(f'newalbum.xaml',output)

def sfile():
    print('sfile-保存build_info.md')
    load_template('build_info.md',noxaml=True)
    save_output_file(f'build_info.md',replaces(templates['build_info.md'],{
        'build_version':BUILD_VERSION
    }))

def music_vote():
    print('music_vote-开始')
    print('music_vote-获取关于音乐投票的issues')
    gh_token = os.environ.get('GITHUB_TOKEN','')
    repo_name = 'wzyaeu/PCLCloudMusicPage'
    response = requests.get(
        f'https://api.github.com/repos/{repo_name}/discussions/categories', 
        headers={
            'Authorization': gh_token,
            'Accept': 'application/vnd.github.v3+json'
        }, params={
            "state": "open",
            "labels": "音乐投票"
        }, verify=False
    )

    issues = response.json()
    print(issues)

    ...

def init():
    print('init-初始化中')
    global OUTPUT_PATH, BASE_PATH, BUILD_VERSION, templates, ncm
    templates = {}
    BUILD_VERSION = secrets.token_hex(4)
    BASE_PATH = os.path.dirname(__file__)
    OUTPUT_PATH = os.path.join(BASE_PATH,'output')
    shutil.rmtree(OUTPUT_PATH,ignore_errors=True)
    os.makedirs(OUTPUT_PATH,exist_ok=True)

    print('init-创建API对象')
    ncm = NeteaseCloudMusicApi()

    print('init-运行mainpage')
    mainpage()

    print('init-运行newsongpage')
    newsongpage()
    
    rank_l = ncm.toplist_detail().data['list']
    print('init-运行rank')
    for listtype in rank_l:
        print(f'init-运行rank-{listtype['name']}')
        global rankncm
        rankncm = NeteaseCloudMusicApi()
        rankpage(listtype) # type: ignore

    print('init-运行ranklist')
    ranklistpage(rank_l)

    print('init-运行highqualitylistpage')
    highqualitylistpage()

    print('init-运行newalbum')
    newalbum()

    print('init-运行sfile')
    sfile()

    print('init-运行music_vote')
    music_vote()

init()