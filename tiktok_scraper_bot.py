import pandas as pd
import asyncio
from playwright.async_api import async_playwright
import re
import os
import random
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

async def scrape_tiktok_metrics(links):
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            locale="vi-VN",
            viewport={'width': 390, 'height': 844}
        )
        page = await context.new_page()

        # Tạo bảng để hiển thị kết quả tổng hợp
        table = Table(title="[bold magenta]TikTok Scraper Live Feed[/bold magenta]", show_header=True, header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("URL", width=30)
        table.add_column("Status", width=12)
        table.add_column("Views", justify="right")
        table.add_column("Likes", justify="right")
        table.add_column("Comments", justify="right")
        table.add_column("Saves", justify="right")
        table.add_column("Shares", justify="right")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Scraping TikTok links...", total=len(links))

            for i, url in enumerate(links):
                progress.update(task, description=f"[yellow]Processing Link #{i+1}[/yellow]")
                
                data = {
                    "URL": url,
                    "Views": "N/A",
                    "Likes": "N/A",
                    "Comments": "N/A",
                    "Saves": "N/A",
                    "Shares": "N/A"
                }
                status = "[green]Success[/green]"
                
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60000)
                    await page.wait_for_timeout(3000)
                    
                    content = await page.content()
                    
                    # Trích xuất dữ liệu
                    play_count = re.search(r'"playCount":(\d+)', content)
                    if play_count: data["Views"] = play_count.group(1)
                    
                    digg_count = re.search(r'"diggCount":(\d+)', content)
                    if digg_count: data["Likes"] = digg_count.group(1)
                    
                    comment_count = re.search(r'"commentCount":(\d+)', content)
                    if comment_count: data["Comments"] = comment_count.group(1)
                    
                    collect_count = re.search(r'"collectCount":(\d+)', content)
                    if collect_count: data["Saves"] = collect_count.group(1)
                    
                    share_count = re.search(r'"shareCount":(\d+)', content)
                    if share_count: data["Shares"] = share_count.group(1)

                except Exception as e:
                    status = f"[red]Error[/red]"
                    console.print(f"[red]Error scraping {url}: {e}[/red]")
                
                # Làm sạch dữ liệu
                for key in ["Likes", "Comments", "Saves", "Shares", "Views"]:
                    val = str(data[key]).replace("\n", "").strip()
                    if val == "": val = "0"
                    data[key] = val

                results.append(data)
                
                # Hiển thị kết quả của link vừa cào xong
                table.add_row(
                    str(i+1),
                    url[:30] + "...",
                    status,
                    data["Views"],
                    data["Likes"],
                    data["Comments"],
                    data["Saves"],
                    data["Shares"]
                )
                
                # Xóa màn hình cũ và in lại bảng mới để cập nhật live
                console.clear()
                console.print(table)
                
                progress.advance(task)
                await asyncio.sleep(random.uniform(1, 2))
        
        await browser.close()
    return results

def main():
    file_path = r"c:\Users\CATTFAN\Desktop\Tiktok\Test_Updated.xlsx"
    if not os.path.exists(file_path):
        console.print(f"[bold red]File not found: {file_path}[/bold red]")
        return

    console.print("[bold green]Reading Excel file...[/bold green]")
    df = pd.read_excel(file_path)
    
    url_col = None
    for col in df.columns:
        if df[col].astype(str).str.contains("tiktok.com").any():
            url_col = col
            break
    
    if not url_col:
        console.print("[bold red]No TikTok links found in the Excel file.[/bold red]")
        return

    links_to_scrape = df[url_col].dropna().head(10)
    indices = links_to_scrape.index
    links = links_to_scrape.tolist()
    
    console.print(f"[bold cyan]Found {len(links)} links. Starting scraper bot...[/bold cyan]")

    results = asyncio.run(scrape_tiktok_metrics(links))

    # Cập nhật dữ liệu vào DataFrame gốc
    for i, res in enumerate(results):
        idx = indices[i]
        df.at[idx, 'Views'] = res['Views']
        df.at[idx, 'Likes'] = res['Likes']
        df.at[idx, 'Comments'] = res['Comments']
        df.at[idx, 'Saves'] = res['Saves']
        df.at[idx, 'Shares'] = res['Shares']

    console.print(f"[bold green]Saving results directly to {file_path}...[/bold green]")
    df.to_excel(file_path, index=False)
    console.print("[bold magenta]Done! All data updated.[/bold magenta]")

if __name__ == "__main__":
    main()
