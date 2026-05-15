
import { t as getJSX } from "./react-vendor-C0IOBbdh.js";

const L = getJSX();

export default function Dashboard() {
  return L.jsxs("div", {
    style: { padding: '24px', color: '#fff' },
    children: [
      L.jsx("h2", { style: { fontSize: '24px', fontWeight: 'bold', marginBottom: '24px' }, children: "เชื่อมต่อสำเร็จ!" }),
      L.jsxs("div", {
        style: { background: '#1a1a1a', padding: '20px', borderRadius: '16px', border: '1px solid #333' },
        children: [
          L.jsx("div", { style: { fontSize: '14px', color: '#00ff00', marginBottom: '8px' }, children: "สถานะ: กำลังซิงค์ข้อมูลจริง" }),
          L.jsx("div", { style: { fontSize: '18px' }, children: "ระบบ AdsPanda AI กำลังดึงข้อมูลจากบัญชีของคุณ..." })
        ]
      })
    ]
  });
}
