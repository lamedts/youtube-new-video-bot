9506  yt-dlp -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" "https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re"
 9507  ./yt-dlp -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" "https://www.youtube.com/playlist?list=PLwiyx1dc3P2JR9N8gQaQN_BCvlSlap7re"
 9508  ./yt-dlp \\n--print filename -o "%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"\n
 9509  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(id)/[%(id)] %(section_number)s - %(title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"
 9510  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(id)/%(id) %(section_number)s - %(section_title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"
 9511  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(id) %(section_number)s - %(section_title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"\n
 9512  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(id)/[%(id)]%(section_number)s - %(title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"
 9513  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(id)s/[%(id)s] %(section_number)s - %(title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"\n
 9514  ./yt-dlp \\n--print filename \\n--split-chapters \\n-o "%(upload_date)s-%(id)s/[%(id)s] %(section_number)s - %(section_title)s.%(ext)s" \\n "https://www.youtube.com/watch?v=kbRTCzjmtR8&t=4s"\n
 9903  mkdir youtube-new-video-bot
