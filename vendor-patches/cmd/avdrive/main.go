// Drives DTLS + SpeakerStart + a real SPEEX narrowband tone, so we can
// verify at the camera whether the audio pipeline actually plays. If any
// 2nd arg is "quiet", payload is zeros. SPEEX frame size for narrowband
// mode 5 is 38 bytes. We send one frame every 20ms, 50 total = 1 second.
package main

import (
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"os"
	"strconv"
	"time"

	"github.com/AlexxIT/go2rtc/pkg/tutk/dtls"
)

func main() {
	host, uid := os.Args[1], os.Args[2]
	port := 32761
	if p := os.Getenv("DRIVE_PORT"); p != "" {
		port, _ = strconv.Atoi(p)
	}
	psk := os.Getenv("CAM_PASS")
	speexFile := os.Getenv("SPEEX_FILE") // path to raw speex frames
	fmt.Printf("dialing %s:%d uid=%s speex=%s\n", host, port, uid, speexFile)
	c, err := dtls.DialDTLS(host, port, uid, "", psk, true)
	if err != nil { fmt.Println("dial:", err); return }
	defer c.Close()
	if err = c.AVClientStart(5 * time.Second); err != nil { fmt.Println("av:", err); return }
	fmt.Println("AV LOGIN OK two-way:", c.HasTwoWayStreaming())

	fmt.Println(">> 848 OpenSpeakerCAM720")
	if err := c.OpenSpeakerCAM720(); err != nil { fmt.Println("w848:", err); return }
	time.Sleep(1500 * time.Millisecond)

	for i := 0; i < 3; i++ {
		if ct, data, err := c.RecvIOCtrlRaw(500 * time.Millisecond); err == nil {
			fmt.Printf("<< IOCtrl 0x%x(%d) %d bytes %s\n", ct, ct, len(data), hex.EncodeToString(data))
		}
	}

	var frames [][]byte
	if speexFile != "" {
		data, err := ioutil.ReadFile(speexFile)
		if err != nil { fmt.Println("speex read:", err); return }
		// Narrowband mode 5 → 38 bytes per frame
		for i := 0; i+38 <= len(data); i += 38 {
			frames = append(frames, data[i:i+38])
		}
		fmt.Printf("loaded %d speex frames\n", len(frames))
	} else {
		pcm := make([]byte, 160)
		for i := range pcm { pcm[i] = 0xFF }
		for i := 0; i < 10; i++ { frames = append(frames, pcm) }
	}

	// Codec 141 = SPEEX, flags for 8kHz mono 16bit: 0 | (0<<2) | (1<<1) = 0x02
	codec := uint16(141)
	flags := byte(0x02)
	if speexFile == "" {
		codec = 0x8A // G.711 A-law for the silent test
	}

	for i, f := range frames {
		if err := c.SendAudioCAM720(codec, flags, f); err != nil {
			fmt.Println("audio err:", err)
			break
		}
		if i < 5 || i%10 == 0 {
			fmt.Printf(">> audio frame %d sent (%d bytes codec=%d flags=0x%x)\n", i+1, len(f), codec, flags)
		}
		time.Sleep(20 * time.Millisecond)
	}

	// Settle & observe
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if ct, data, err := c.RecvIOCtrlRaw(200 * time.Millisecond); err == nil {
			fmt.Printf("<< IOCtrl 0x%x %d bytes %s\n", ct, len(data), hex.EncodeToString(data))
		}
	}
	_ = binary.LittleEndian
}
