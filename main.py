from MusicLibrary.neteaseCloudMusicApi import NeteaseCloudMusicApi

import os
import shutil
import json
import secrets
import requests
import re
from datetime import datetime

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
             .replace('"', '&quot;')
             .replace("'", '&apos;')
    )

def iso_to_timestamp(iso_str):
    return int(datetime.fromisoformat(iso_str.replace('Z', '+00:00')).timestamp())

def label_template_load():
    load_template('label_paid')
    load_template('label_vip')
    load_template('label_votecount')
    load_template('label_rank_down')
    load_template('label_rank_up')
    load_template('label_rank_new')

def mainpage():
    print('mainpage-开始')
    print('mainpage-加载模板')
    load_template('mainpage')
    load_template('music')
    label_template_load()

    print('mainpage-获取api数据')
    music_data: dict = ncm.playlist_track_all(3779629).data # type: ignore
    music_list = music_data['songs'][:10]
    print('mainpage-构建页面')
    output = replaces(templates['mainpage'],{
        'music':'\n'.join([
            replaces(templates['music'],{
                'tag':'',
                'label':''.join([
                    templates['label_vip'] if m['fee'] == 1 else '',
                    templates['label_paid'] if m['fee'] == 4 else '',
                ]),
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
    label_template_load()

    print(f'newsongpage-获取api数据')
    music_data: dict = ncm.top_song(0).data # type: ignore

    print('newsongpage-构建页面')
    output = replaces(templates['newsongpage'],{
        'music':'\n'.join([
            replaces(templates['music'],{
                'tag':'',
                'label':''.join([
                    templates['label_vip'] if m['fee'] == 1 else '',
                    templates['label_paid'] if m['fee'] == 4 else '',
                ]),
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
    def get_music_rank_diff_label(mid, rank):
        if mid not in rank_diff['rank']:
            rank_diff['rank'][mid] = {'n':rank,'d':None}
            return replaces(templates['label_rank_new'],{})

        if rank_diff['update'] < listtype['updateTime']: # 页面更新时间晚于榜单更新时间
            if rank < rank_diff['rank'][mid]['n']: # 排名升了
                rank_diff['rank'][mid] = {'n':rank,'d':rank-rank_diff['rank'][mid]['n']}
                return replaces(templates['label_rank_up'],{
                    'num':-rank_diff['rank'][mid]['d']
                })
            elif rank > rank_diff['rank'][mid]['n']: # 排名降了
                rank_diff['rank'][mid] = {'n':rank,'d':rank-rank_diff['rank'][mid]['n']}
                return replaces(templates['label_rank_down'],{
                    'num':rank_diff['rank'][mid]['d']
                })
            else:
                rank_diff['rank'][mid] = {'n':rank,'d':0}
                return ''
        else: # 没更新
            if rank_diff['rank'][mid]['d'] == None:
                return replaces(templates['label_rank_new'],{})
            elif rank_diff['rank'][mid]['d'] > 0:
                return replaces(templates['label_rank_up'],{
                    'num':-rank_diff['rank'][mid]['d']
                })
            elif rank_diff['rank'][mid]['d'] < 0:
                return replaces(templates['label_rank_down'],{
                    'num':rank_diff['rank'][mid]['d']
                })
            else:
                return ''

    print(f'rankpage-开始-{listtype['name']}-{listtype['id']}')
    print('rankpage-加载模板')
    load_template('music')
    load_template('rankpage')
    load_template('rankpage-next')
    load_template('rankpage-musictag')
    label_template_load()

    print(f'rankpage-获取api数据')
    music_data = rankncm.playlist_track_all(listtype['id'])
    music_list = music_data.data['songs']
    chunk_size = 20
    music_lists = [music_list[i:i + chunk_size] for i in range(0, len(music_list), chunk_size)] if len(music_list) > 0 else [[]]
    all_output = []

    print(f'rankpage-获取排名差分')
    rank_diff_path = os.path.join(BASE_PATH,'data',f'rankdiff_{listtype['id']}.json')
    if os.path.exists(rank_diff_path):
        with open(rank_diff_path,'r',encoding='utf-8') as f:
            rank_diff = json.load(f)
    else:
        rank_diff = {'update':listtype['updateTime'],'rank':{}}

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
                    'label':''.join([
                        get_music_rank_diff_label(m['id'], index),
                        templates['label_vip'] if m['fee'] == 1 else '',
                        templates['label_paid'] if m['fee'] == 4 else ''
                    ]),
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

    print('rankpage-保存排名差分')
    if rank_diff['update'] < listtype['updateTime']:
        rank_diff['update'] = listtype['updateTime']
    with open(rank_diff_path,'w',encoding='utf-8') as f:
        json.dump(rank_diff, f)

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
                'label':'',
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
                'label':'',
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

def gh_request(token, method, url, **kwargs):
    """GitHub REST API 请求封装"""
    headers = {
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    if 'headers' in kwargs:
        headers.update(kwargs.pop('headers'))
    response = requests.request(
        method, 
        f'https://api.github.com/repos/{repo_name}{url}', 
        headers=headers, 
        **kwargs,
        verify=not test_environment
    )
    response.raise_for_status()
    return response

def gh_graphql(token, query, variables=None):
    """GitHub GraphQL API 请求封装"""
    body = {'query': query}
    if variables:
        body['variables'] = variables
    response = requests.post(
        'https://api.github.com/graphql',
        headers={
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github.v3+json'
        },
        json=body,
        verify=not test_environment
    )
    resp_json = response.json()
    if 'errors' in resp_json:
        print(f'GraphQL 错误: {resp_json["errors"]}')
    response.raise_for_status()
    return resp_json

def music_vote():
    print('music_vote-开始')
    global gh_token, repo_name
    gh_token = os.environ.get('MY_GITHUB_TOKEN','')
    repo_name = 'wzyaeu/PCLCloudMusicPage'

    print('music_vote-获取音乐投票的数据')
    accepted_submission_filepath = os.path.join(BASE_PATH, 'accepted_submission.json')
    if os.path.exists(accepted_submission_filepath):
        with open(accepted_submission_filepath, 'r', encoding='utf-8') as f:
            accepted_submission = json.load(f)

        for accs in accepted_submission[:]:
            response = gh_request(gh_token, 'GET', f'/issues/{accs['issueid']}')
            try:
                response.raise_for_status()
            except:
                # 检测到已失效的 issue，删除对应的 discussion，并从 accepted_submission 中移除此项
                print(f'music_vote-Issue(#{accs["issueid"]})已失效，正在清理...')
                owner, repo = repo_name.split('/')
                # 通过 GraphQL 获取 discussion 的 node ID
                resp_json = gh_graphql(gh_token, '''
                    query($owner: String!, $repo: String!, $number: Int!) {
                        repository(owner: $owner, name: $repo) {
                            discussion(number: $number) {
                                id
                            }
                        }
                    }
                ''', variables={
                    'owner': owner,
                    'repo': repo,
                    'number': accs['discussionid']
                })
                discussion_node_id = resp_json['data']['repository']['discussion']['id']
                # 删除 discussion
                gh_graphql(gh_token, '''
                    mutation($discussionId: ID!) {
                        deleteDiscussion(input: {id: $discussionId}) {
                            clientMutationId
                        }
                    }
                ''', variables={
                    'discussionId': discussion_node_id
                })
                print(f'music_vote-Discussion(#{accs["discussionid"]})已删除！')
                accepted_submission.remove(accs)
    else:
        accepted_submission = [] # 受理的投稿
        with open(accepted_submission_filepath, 'w', encoding='utf-8') as f:
            json.dump([],f)
    print('music_vote-获取关于音乐投票的issues')
    response = gh_request(gh_token, 'GET', f'/issues', params={
        'state': 'all',
        'labels': '音乐投票'
    })
    issues = response.json()

    print('music_vote-格式化数据')
    vote_data: dict[str, list[dict]] = {}
    for issue in issues:
        if frozenset({label['name'] for label in issue['labels']}) in \
        {frozenset({'音乐投票','音乐投票-待确认'}),frozenset({'音乐投票','音乐投票-已受理'})}:
            match = re.search(r'### 音乐 ID\n\n(\d+)\n\n', issue['body'])
            if match: music_id = match.group(1)
            else: music_id = ''

            if issue['user']['login'] not in vote_data: 
                vote_data[issue['user']['login']] = []
            
            vote_data[issue['user']['login']].append({
                'issueid':issue['number'],
                'musicid':music_id,
                'vaild':bool(match),
                'time':iso_to_timestamp(issue['created_at']),
                'labels':{label['name'] for label in issue['labels']}
            })
    print(f'music_vote-已获取{len(vote_data.keys())}个用户共{sum([len(v) for v in vote_data.values()])}个投稿')

    allissues = [x for lst in [[issue | {'user':user} for issue in issues] for user, issues in vote_data.items()] for x in lst] # 将issues每一项的每一项都添加user键并合并成一个列表
    allissues.sort(key=lambda x: x['time'])
    count = {} # 每个用户的投稿的计数
    musicids = [] # 记录musicid，防止重复
    for issue in allissues:
        if issue['user'] not in count:
            count[issue['user']] = 0
        if len(issue['labels']) != 2:
            continue
        if issue['labels'] != {'音乐投票','音乐投票-已受理'}:
            count[issue['user']] += 1
            try:
                assert count[issue['user']] <= 3, '投稿数超过上限（3个）'
                assert issue['vaild'], '未识别到音乐ID'
                assert issue['musicid'] not in musicids, '此音乐ID重复投稿'
                song_detail = ncm.song_detail(ids=issue['musicid']).data
                assert song_detail['code'] == 200, '音乐ID错误'
                
                print(f'music_vote-Issue(#{issue['issueid']})已受理！')
                music_name = song_detail['songs'][0]['name']
                music_imageurl = song_detail['songs'][0]['al']['picUrl']
                submitter_name = issue['user']
                submitter_url = f'https://github.com/{submitter_name}'
                music_url = f'https://music.163.com/#/song?id={issue['musicid']}'
                
                # 通过 GraphQL API 获取仓库 ID、MusicVote 分类 ID、以及标签 node_id
                owner, repo = repo_name.split('/')
                resp_json = gh_graphql(gh_token, '''
                    query($owner: String!, $repo: String!) {
                        repository(owner: $owner, name: $repo) {
                            id
                            discussionCategories(first: 20) {
                                nodes {
                                    id
                                    name
                                    slug
                                }
                            }
                            labels(first: 100) {
                                nodes {
                                    id
                                    name
                                }
                            }
                        }
                    }
                ''', variables={
                    'owner': owner,
                    'repo': repo
                }) 
                repo_data = resp_json['data']['repository']
                repository_id = repo_data['id']
                
                # 找到 MusicVote 分类的 ID
                category_id = next((c['id'] for c in repo_data['discussionCategories']['nodes'] if c.get('slug') == 'musicvote' or c.get('name') == 'MusicVote'), None)
                
                # 找到标签 node_id
                label_map = {label['name']: label['id'] for label in repo_data['labels']['nodes']}
                label_ids = [label_map[name] for name in ['音乐投票', '音乐投票-进行中'] if name in label_map]
                
                # 通过 GraphQL 创建 Discussion
                discussion_body = f'# 音乐投票\n投稿人：[{submitter_name}]({submitter_url})\n投稿音乐：[{music_name}]({music_url})\n\n<img width="170" height="170" alt="image" src="{music_imageurl}" />\n\n---\n点击下方的"↑"箭头投票！'
                discussion_title = f'[音乐投票] {music_name}'
                
                resp_json = gh_graphql(gh_token, '''
                    mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
                        createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId, title: $title, body: $body}) {
                            discussion {
                                id
                                number
                            }
                        }
                    }
                ''', variables={
                    'repositoryId': repository_id,
                    'categoryId': category_id,
                    'title': discussion_title,
                    'body': discussion_body
                })
                discussion = resp_json['data']['createDiscussion']['discussion']
                discussion_node_id = discussion['id']
                discussion_number = discussion['number']
                print(f'music_vote-Discussion(#{discussion_number})已创建！')
                
                # 给 Discussion 添加标签
                if label_ids:
                    gh_graphql(gh_token, '''
                        mutation($discussionId: ID!, $labelIds: [ID!]!) {
                            addLabelsToLabelable(input: {labelableId: $discussionId, labelIds: $labelIds}) {
                                clientMutationId
                            }
                        }
                    ''', variables={
                        'discussionId': discussion_node_id,
                        'labelIds': label_ids
                    })
                
                discussion_url = f'https://github.com/{repo_name}/discussions/{discussion_number}'
                gh_request(gh_token, 'POST', f'/issues/{issue['issueid']}/comments', json={
                    'body': f'[BOT回复] 您的投稿已受理！此投稿的投票discussion：{discussion_url}',
                })

                # 关闭原 issue 并附上 "音乐投票-已受理" 标签
                gh_request(gh_token, 'PUT', f'/issues/{issue['issueid']}/labels', json={
                    'labels': ['音乐投票','音乐投票-已受理']
                })
                
                gh_request(gh_token, 'PATCH', f'/issues/{issue['issueid']}', json={
                    'state': 'closed',
                    'state_reason': 'completed'
                })
                musicids.append(issue['musicid'])
                accepted_submission.append({
                    'musicid':issue['musicid'],
                    'issueid':issue['issueid'],
                    'discussionid':discussion_number,
                })
            except Exception as e:
                print(f'music_vote-Issue(#{issue['issueid']})因"{str(e)}"而无法受理。')
                gh_request(gh_token, 'POST', f'/issues/{issue['issueid']}/comments', json={
                    'body': f'[BOT回复] 您的投稿错误而无法受理！原因: "{str(e)}"',
                })
                gh_request(gh_token, 'PUT', f'/issues/{issue['issueid']}/labels', json={
                    'labels': ['音乐投票','音乐投票-无效']
                })
                gh_request(gh_token, 'PATCH', f'/issues/{issue['issueid']}', json={
                    'state': 'closed',
                    'state_reason': 'not_planned'
                })
        elif issue['labels'] == {'音乐投票','音乐投票-已受理'}:
            musicids.append(issue['musicid'])
    with open(accepted_submission_filepath, 'w', encoding='utf-8') as f:
        json.dump(accepted_submission,f)
    return accepted_submission

def musicvotepage(accepted_submissions):
    def music_vote_count(discussionid):
        owner, repo = repo_name.split('/')
        resp_json = gh_graphql(gh_token, '''
            query($owner: String!, $repo: String!, $number: Int!) {
                repository(owner: $owner, name: $repo) {
                    discussion(number: $number) {
                        upvoteCount
                    }
                }
            }
        ''', variables={
            'owner': owner,
            'repo': repo,
            'number': discussionid
        })
        return int(resp_json['data']['repository']['discussion']['upvoteCount'])
    print('musicvotepage-开始')
    print('musicvotepage-加载模板')
    load_template('musicvotepage')
    load_template('rankpage-musictag')
    label_template_load()

    print(f'musicvotepage-获取api数据')
    accepted_submissions = {accepted_submission['musicid']:accepted_submission for accepted_submission in accepted_submissions}
    music_data: list = ncm.song_detail(ids=','.join([
        accepted_submission_musicid for accepted_submission_musicid in accepted_submissions.keys()
    ])).data['songs']

    print(f'musicvotepage-数据排序')
    music_data = [music | {'vote':music_vote_count(accepted_submissions[str(music['id'])]['discussionid'])} for music in music_data]
    music_data.sort(key=lambda x: x['vote'],reverse=True)

    chunk_size = 20
    music_lists = [music_data[i:i + chunk_size] for i in range(0, len(music_data), chunk_size)] if len(music_data) > 0 else [[]]
    all_output = []
    print(f'musicvotepage-构建页面')
    for vlindex, vl in enumerate(music_lists, start=1):
        print(f'musicvotepage-构建页面-{vlindex}/{len(music_lists)}')
        output = replaces(templates['musicvotepage'],{
            'num':vlindex,
            'listname':'音乐投票榜',
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
                    'label':''.join([
                        replaces(templates['label_votecount'],{
                            'count':m['vote'],
                            'voteurl':f'https://github.com/wzyaeu/PCLCloudMusicPage/discussions/{accepted_submissions[str(m['id'])]['discussionid']}',
                        }),
                        templates['label_vip'] if m['fee'] == 1 else '',
                        templates['label_paid'] if m['fee'] == 4 else '',
                    ]),
                }) for index, m in enumerate(vl,start=1+(vlindex-1)*20)
            ]),
            'next': '' if vlindex == len(music_lists) else replaces(templates['rankpage-next'],{
                'num':vlindex+1,
                'ltype':'vote'
            }),
        })

        all_output.append(output)
    print('musicvotepage-保存输出文件')
    for index, o in enumerate(all_output, start=1):
        print(f'musicvotepage-保存输出文件-{index}/{len(music_lists)}')
        save_output_file(f'vote_rank_{index}.json',json.dumps(
            {
                'Title': f'Music 云音乐 投票排行榜 | 第 {index} / {len(music_lists)} 页'
            }
        ,ensure_ascii=False))
        save_output_file(f'vote_rank_{index}.xaml',o)

def init():
    print('init-初始化中')
    global OUTPUT_PATH, BASE_PATH, BUILD_VERSION, templates, ncm, test_environment
    templates = {}
    BUILD_VERSION = secrets.token_hex(4)
    BASE_PATH = os.path.dirname(__file__)
    OUTPUT_PATH = os.path.join(BASE_PATH,'output')
    shutil.rmtree(OUTPUT_PATH,ignore_errors=True)
    os.makedirs(OUTPUT_PATH,exist_ok=True)
    os.makedirs(os.path.join(BASE_PATH,'data'),exist_ok=True)

    test_environment = os.path.exists(os.path.join(BASE_PATH,'test_environment'))

    if test_environment:
        from urllib3.exceptions import InsecureRequestWarning
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning) # type: ignore

    print('init-创建API对象')
    ncm = NeteaseCloudMusicApi()

    print('init-运行mainpage')
    mainpage()

    print('init-运行newsongpage')
    newsongpage()
    
    print('init-运行music_vote')
    accepted_submissions = music_vote()

    print('init-运行musicvotepage')
    musicvotepage(accepted_submissions)

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

init()