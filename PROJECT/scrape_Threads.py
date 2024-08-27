import sys              # xu ly tham so dong lenh
import json             # lam viec voi JSON
from typing import Dict # dinh nghia kieu du lieu tu thu vien typing
import jmespath         # truy van va trich xuat du lieu JSON
from parsel import Selector                     # phan tich HTML
from playwright.sync_api import sync_playwright # tu dong hoa tai trang web
from nested_lookup import nested_lookup         # tim kiem trong cau truc long nhau

def parse_thread(data: Dict) -> Dict:
    result = jmespath.search(
        """{
            text: post.caption.text,
            published_on: post.taken_at,
            id: post.id,
            pk: post.pk,
            code: post.code,
            username: post.user.username,
            user_pic: post.user.profile_pic_url,
            user_verified: post.user.is_verified,
            user_pk: post.user.pk,
            user_id: post.user.id,
            has_audio: post.has_audio,
            like_count: post.like_count,
            reply_count: post.text_post_app_info.direct_reply_count, 
            images: post.carousel_media[].image_versions2.candidates[1].url || post.image_versions2.candidates[1].url,
            videos: post.video_versions[].url
        }""",
        data,
    )
    result["videos"] = list(set(result["videos"] or []))
    if result["reply_count"] and type(result["reply_count"]) != int:
        result["reply_count"] = int(result["reply_count"].split(" ")[0])
    result[
        "url"
    ] = f"https://www.threads.net/@{result['username']}/post/{result['code']}"
    return result

def parse_profile(data: Dict) -> Dict:
    result = jmespath.search(
        """{
            is_private: text_post_app_is_private,
            is_verified: is_verified,
            profile_pic: hd_profile_pic_versions[-1].url,
            username: username,
            full_name: full_name,
            bio: biography,
            bio_links: bio_links[].url,
            followers: follower_count
        }""",
        data,
    )
    result["url"] = f"https://www.threads.net/@{result['username']}"
    return result

def scrape_profile(url: str) -> dict:
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        page = context.new_page()

        page.goto(url)
        page.wait_for_selector("[data-pressable-container=true]")
        selector = Selector(page.content())
        
    parsed = {
        "user": {},
        "threads": [],
    }
    
    hidden_datasets = selector.css('script[type="application/json"][data-sjs]::text').getall()
    for hidden_dataset in hidden_datasets:
        if '"ScheduledServerJS"' not in hidden_dataset:
            continue
        is_profile = 'follower_count' in hidden_dataset
        is_threads = 'thread_items' in hidden_dataset
        if not is_profile and not is_threads:
            continue
        data = json.loads(hidden_dataset)
        if is_profile:
            user_data = nested_lookup('user', data)
            parsed['user'] = parse_profile(user_data[0])
        if is_threads:
            thread_items = nested_lookup('thread_items', data)
            threads = [
                parse_thread(t) for thread in thread_items for t in thread
            ]
            parsed['threads'].extend(threads)
    return parsed

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scrape_profiles.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    data = scrape_profile(url)
    print(json.dumps(data, indent=2, ensure_ascii=False))